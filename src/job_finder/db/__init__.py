"""Database module for Supabase integration."""

from job_finder.db.client import (
    SupabaseNotConfiguredError,
    get_supabase_client,
    init_supabase,
    reset_client,
)

__all__ = [
    "SupabaseNotConfiguredError",
    "get_supabase_client",
    "init_supabase",
    "reset_client",
]
