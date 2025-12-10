from __future__ import annotations

import asyncio
import re
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Sequence

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message

from job_finder.models import RawPost
from job_finder.state import State

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
) -> List[Message]:
    offset_date = datetime.now(tz=timezone.utc) - timedelta(hours=hours_lookback)
    messages: List[Message] = []
    async for message in client.iter_messages(
        channel,
        min_id=last_message_id or 0,
        offset_date=offset_date,
        reverse=True,
    ):
        messages.append(message)
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
    state: State,
    hours_lookback: int,
) -> List[RawPost]:
    tasks = [
        _collect_channel_messages(
            client,
            channel,
            state.get_last_message_id(channel),
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
