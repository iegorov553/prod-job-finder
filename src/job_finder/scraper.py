from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Mapping, Sequence

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message

from job_finder.models import RawPost

# Type alias for channel state mapping (channel -> last_message_id)
ChannelStateMap = Mapping[str, int | None]

URL_PATTERN = re.compile(r"https?://\S+")


def create_client(
    api_id: int,
    api_hash: str,
    session_name: str,
    string_session: str | None = None,
) -> TelegramClient:
    if string_session:
        return TelegramClient(StringSession(string_session), api_id, api_hash)
    return TelegramClient(session_name, api_id, api_hash)


async def _collect_channel_messages(
    client: TelegramClient,
    channel: str,
    last_message_id: int | None,
    hours_lookback: int,
    max_messages: int = 500,
) -> List[Message]:
    """Collect messages from a channel.

    Two strategies depending on whether we have last_message_id:
    1. With last_message_id: get messages with ID > last_message_id (new messages)
    2. Without last_message_id: get recent messages within hours_lookback window
    """
    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(hours=hours_lookback)
    messages: List[Message] = []

    if last_message_id:
        # Channel with known state: get new messages since last_message_id
        async for message in client.iter_messages(
            channel,
            min_id=last_message_id,
            limit=max_messages,
            reverse=True,
        ):
            msg_date = message.date.replace(tzinfo=timezone.utc)
            if msg_date >= cutoff_date:
                messages.append(message)
    else:
        # New channel: get recent messages within hours_lookback window
        # Iterate from newest to oldest, stop when we hit old messages
        async for message in client.iter_messages(
            channel,
            limit=max_messages,
        ):
            msg_date = message.date.replace(tzinfo=timezone.utc)
            if msg_date < cutoff_date:
                break  # Reached messages older than cutoff, stop
            messages.append(message)
        # Reverse to get chronological order (oldest first)
        messages.reverse()

    return messages


def _extract_links(text: str) -> List[str]:
    return URL_PATTERN.findall(text)


def _build_source_link(channel: str, message_id: int) -> str:
    channel_id = channel.removeprefix("@")
    return f"https://t.me/{channel_id}/{message_id}"


def _message_to_raw_post(channel: str, message: Message) -> RawPost:
    text = message.message or ""
    links = _extract_links(text)
    source_link = _build_source_link(channel, message.id)
    date_iso = message.date.astimezone(timezone.utc).isoformat()
    return RawPost(
        id=message.id,
        channel=channel,
        date=date_iso,
        text=text,
        links=links,
        source_link=source_link,
    )


async def fetch_new_posts(
    client: TelegramClient,
    channels: Sequence[str],
    channel_states: ChannelStateMap,
    hours_lookback: int,
) -> List[RawPost]:
    """Fetch new posts from channels since last known message IDs.

    Args:
        client: Telethon client
        channels: List of channel usernames
        channel_states: Mapping of channel -> last_message_id
        hours_lookback: How far back to look for messages

    Returns:
        List of RawPost objects
    """
    tasks = [
        _collect_channel_messages(
            client,
            channel,
            channel_states.get(channel),
            hours_lookback=hours_lookback,
        )
        for channel in channels
    ]
    collected: List[List[Message]] = await asyncio.gather(*tasks)
    posts: List[RawPost] = []
    for channel, messages in zip(channels, collected):
        for message in messages:
            posts.append(_message_to_raw_post(channel, message))
    return posts


def get_max_message_id(posts: Iterable[RawPost], channel: str) -> int | None:
    ids = [post.id for post in posts if post.channel == channel]
    if not ids:
        return None
    return max(ids)
