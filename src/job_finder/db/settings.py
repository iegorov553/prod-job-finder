"""CRUD operations for settings table.

This module provides functions to manage bot settings in Supabase,
storing dynamic configuration that can be changed at runtime.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, cast

from job_finder.db.client import get_supabase_client
from job_finder.db.models import SettingsDB, SettingsUpdate

logger = logging.getLogger(__name__)

TABLE_NAME = "settings"


def get_settings() -> Optional[SettingsDB]:
    """Get current settings from the database.

    Returns singleton settings record or None if not initialized.

    Returns:
        SettingsDB if found, None otherwise
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").limit(1).execute()

    if not response.data:
        return None

    return cast(SettingsDB, SettingsDB.model_validate(response.data[0]))


def upsert_settings(update: SettingsUpdate) -> Optional[SettingsDB]:
    """Update settings using upsert.

    Creates settings record if it doesn't exist, updates otherwise.
    Only provided (non-None) fields will be updated.

    Args:
        update: SettingsUpdate with fields to update

    Returns:
        Updated SettingsDB
    """
    client = get_supabase_client()

    # Get current settings to preserve existing values
    current = get_settings()
    if current:
        # Merge update with existing settings
        payload = {"id": current.id}
        payload.update(update.to_db_dict())
    else:
        # Create new with defaults
        payload = update.to_db_dict()

    response = client.table(TABLE_NAME).upsert(payload).execute()

    if not response.data:
        return None

    return cast(SettingsDB, SettingsDB.model_validate(response.data[0]))


def ensure_settings_exist() -> SettingsDB:
    """Ensure settings record exists, creating with defaults if needed.

    This should be called at application startup to guarantee
    the settings singleton exists.

    Returns:
        SettingsDB (existing or newly created)
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").limit(1).execute()

    if response.data:
        return cast(SettingsDB, SettingsDB.model_validate(response.data[0]))

    # Create default settings
    default_payload: dict[str, Any] = {
        "channels": [],
        "scheduler_enabled": False,
    }

    insert_response = client.table(TABLE_NAME).insert(default_payload).execute()
    return cast(SettingsDB, SettingsDB.model_validate(insert_response.data[0]))


def update_settings_field(field_name: str, value: Any) -> Optional[SettingsDB]:
    """Update a single settings field.

    Convenience function for updating one field at a time.

    Args:
        field_name: Name of the field to update
        value: New value for the field

    Returns:
        Updated SettingsDB if successful, None otherwise
    """
    client = get_supabase_client()

    # Use neq to match any row (singleton workaround)
    response = client.table(TABLE_NAME).update({field_name: value}).neq("id", "").execute()

    if not response.data:
        return None

    return cast(SettingsDB, SettingsDB.model_validate(response.data[0]))


def reset_custom_prompt() -> Optional[SettingsDB]:
    """Reset custom_prompt to None (use default).

    Returns:
        Updated SettingsDB if successful, None otherwise
    """
    return update_settings_field("custom_prompt", None)


def reset_llm_temperature() -> Optional[SettingsDB]:
    """Reset llm_temperature to None (use API default).

    Returns:
        Updated SettingsDB if successful, None otherwise
    """
    return update_settings_field("llm_temperature", None)


def add_channels(channels: list[str]) -> Optional[SettingsDB]:
    """Add channels to the list.

    Merges new channels with existing ones, avoiding duplicates.

    Args:
        channels: List of channel usernames to add

    Returns:
        Updated SettingsDB if successful, None otherwise
    """
    current = get_settings()
    if not current:
        # Create settings with these channels
        return upsert_settings(SettingsUpdate(channels=channels))

    existing = set(current.channels or [])
    new_channels = list(current.channels or [])
    for ch in channels:
        if ch not in existing:
            new_channels.append(ch)
            existing.add(ch)

    return update_settings_field("channels", new_channels)


def remove_channels(channels: list[str]) -> Optional[SettingsDB]:
    """Remove channels from the list.

    Args:
        channels: List of channel usernames to remove

    Returns:
        Updated SettingsDB if successful, None otherwise
    """
    current = get_settings()
    if not current:
        return None

    remove_set = set(channels)
    new_channels = [ch for ch in (current.channels or []) if ch not in remove_set]

    return update_settings_field("channels", new_channels)


def set_scheduler(enabled: bool, time_utc: Optional[str]) -> Optional[SettingsDB]:
    """Set scheduler configuration.

    Args:
        enabled: Whether scheduler should be enabled
        time_utc: Time in HH:MM format (UTC), or None to disable

    Returns:
        Updated SettingsDB if successful, None otherwise
    """
    client = get_supabase_client()

    # Update both fields at once
    response = (
        client.table(TABLE_NAME)
        .update({"scheduler_enabled": enabled, "scheduler_time_utc": time_utc})
        .neq("id", "")
        .execute()
    )

    if not response.data:
        return None

    return cast(SettingsDB, SettingsDB.model_validate(response.data[0]))
