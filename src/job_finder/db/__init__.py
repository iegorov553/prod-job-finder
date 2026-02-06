"""Database module for Supabase integration."""

from job_finder.db.client import (
    SupabaseNotConfiguredError,
    get_supabase_client,
    init_supabase,
    reset_client,
)
from job_finder.db.settings import (
    ensure_settings_exist,
    get_settings,
    reset_custom_prompt,
    reset_llm_temperature,
    update_settings_field,
    upsert_settings,
)

__all__ = [
    "SupabaseNotConfiguredError",
    "get_supabase_client",
    "init_supabase",
    "reset_client",
    # Settings CRUD
    "ensure_settings_exist",
    "get_settings",
    "reset_custom_prompt",
    "reset_llm_temperature",
    "update_settings_field",
    "upsert_settings",
]
