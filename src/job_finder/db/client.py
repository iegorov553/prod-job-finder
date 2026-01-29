"""Supabase client singleton module.

Provides a singleton pattern for Supabase client to ensure
only one connection is created per application lifecycle.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

_client: "Client | None" = None


class SupabaseNotConfiguredError(Exception):
    """Raised when Supabase credentials are not configured."""


def init_supabase(url: str | None, key: str | None) -> "Client":
    """Initialize the Supabase client singleton.

    Args:
        url: Supabase project URL (e.g., https://xxx.supabase.co)
        key: Supabase service_role key for full access

    Returns:
        Initialized Supabase client

    Raises:
        SupabaseNotConfiguredError: If url or key is not provided
    """
    global _client

    if not url or not key:
        raise SupabaseNotConfiguredError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment"
        )

    if _client is not None:
        logger.debug("Supabase client already initialized, returning existing instance")
        return _client

    from supabase import create_client

    _client = create_client(url, key)
    logger.info("Supabase client initialized successfully")
    return _client


def get_supabase_client() -> "Client":
    """Get the initialized Supabase client.

    Returns:
        The Supabase client singleton

    Raises:
        SupabaseNotConfiguredError: If client was not initialized
    """
    if _client is None:
        raise SupabaseNotConfiguredError(
            "Supabase client not initialized. Call init_supabase() first."
        )
    return _client


def reset_client() -> None:
    """Reset the client singleton (for testing purposes)."""
    global _client
    _client = None
