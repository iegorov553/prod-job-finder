"""CRUD operations for channel_states table.

This module provides functions to manage channel state in Supabase,
replacing the file-based state.json approach.
"""

from __future__ import annotations

import logging
from typing import List, Optional, cast

from job_finder.db.client import get_supabase_client
from job_finder.db.models import ChannelStateCreate, ChannelStateDB

logger = logging.getLogger(__name__)

TABLE_NAME = "channel_states"


def get_channel_state(channel: str) -> Optional[ChannelStateDB]:
    """Get channel state by channel name.

    Args:
        channel: Channel username (e.g., "@channel_name")

    Returns:
        ChannelStateDB if found, None otherwise
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").eq("channel", channel).execute()

    if not response.data:
        return None

    return cast(ChannelStateDB, ChannelStateDB.model_validate(response.data[0]))


def get_all_channel_states() -> List[ChannelStateDB]:
    """Get all channel states from the database.

    Returns:
        List of ChannelStateDB objects
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").execute()

    return [ChannelStateDB.model_validate(row) for row in response.data]


def upsert_channel_state(data: ChannelStateCreate) -> ChannelStateDB:
    """Create or update a channel state.

    Uses upsert with channel as the conflict key to handle
    both insert and update in a single operation.

    Args:
        data: Channel state data to upsert

    Returns:
        The created or updated ChannelStateDB
    """
    client = get_supabase_client()
    payload = data.model_dump(exclude_none=True)

    response = client.table(TABLE_NAME).upsert(payload).execute()

    return cast(ChannelStateDB, ChannelStateDB.model_validate(response.data[0]))


def update_last_message_id(channel: str, last_message_id: int) -> ChannelStateDB:
    """Convenience function to update only the last_message_id.

    Args:
        channel: Channel username
        last_message_id: New last message ID to set

    Returns:
        Updated ChannelStateDB
    """
    data = ChannelStateCreate(channel=channel, last_message_id=last_message_id)
    return upsert_channel_state(data)


def delete_channel_state(channel: str) -> bool:
    """Delete a channel state.

    Args:
        channel: Channel username to delete

    Returns:
        True if deleted, False if not found
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).delete().eq("channel", channel).execute()

    return len(response.data) > 0


def ensure_channels_exist(channels: List[str]) -> List[ChannelStateDB]:
    """Ensure all channels have state records.

    Creates new records for channels that don't exist yet,
    leaves existing records unchanged.

    Args:
        channels: List of channel usernames

    Returns:
        List of all ChannelStateDB for the given channels
    """
    existing = {state.channel: state for state in get_all_channel_states()}
    result: List[ChannelStateDB] = []

    for channel in channels:
        if channel in existing:
            result.append(existing[channel])
        else:
            new_state = upsert_channel_state(ChannelStateCreate(channel=channel))
            result.append(new_state)
            logger.info("Created new channel state for %s", channel)

    return result
