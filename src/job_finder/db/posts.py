"""CRUD operations for posts table.

This module provides functions to manage posts in Supabase,
storing all Telegram messages fetched from channels.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, cast

from job_finder.db.client import get_supabase_client
from job_finder.db.models import PostCreate, PostDB, PostUpdate

logger = logging.getLogger(__name__)

TABLE_NAME = "posts"


def create_post(data: PostCreate) -> PostDB:
    """Create a single post in the database.

    Args:
        data: Post data to create

    Returns:
        Created PostDB with generated id
    """
    client = get_supabase_client()
    payload = data.model_dump(mode="json")

    response = client.table(TABLE_NAME).insert(payload).execute()

    return cast(PostDB, PostDB.model_validate(response.data[0]))


def create_posts_batch(posts: List[PostCreate]) -> List[PostDB]:
    """Create multiple posts in a single batch operation.

    Uses upsert to handle duplicate telegram_id/channel combinations
    gracefully (ignores duplicates).

    Args:
        posts: List of posts to create

    Returns:
        List of created PostDB objects
    """
    if not posts:
        return []

    client = get_supabase_client()
    payloads = [post.model_dump(mode="json") for post in posts]

    response = (
        client.table(TABLE_NAME).upsert(payloads, on_conflict="channel,telegram_id").execute()
    )

    return [PostDB.model_validate(row) for row in response.data]


def get_post_by_id(post_id: int) -> Optional[PostDB]:
    """Get a post by its database ID.

    Args:
        post_id: Database ID of the post

    Returns:
        PostDB if found, None otherwise
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").eq("id", post_id).execute()

    if not response.data:
        return None

    return cast(PostDB, PostDB.model_validate(response.data[0]))


def get_post_by_telegram_id(channel: str, telegram_id: int) -> Optional[PostDB]:
    """Get a post by channel and Telegram message ID.

    Args:
        channel: Channel username
        telegram_id: Telegram message ID

    Returns:
        PostDB if found, None otherwise
    """
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME)
        .select("*")
        .eq("channel", channel)
        .eq("telegram_id", telegram_id)
        .execute()
    )

    if not response.data:
        return None

    return cast(PostDB, PostDB.model_validate(response.data[0]))


def get_pending_posts(limit: int = 100) -> List[PostDB]:
    """Get posts that haven't been analyzed yet.

    Args:
        limit: Maximum number of posts to return

    Returns:
        List of PostDB with analysis_status='pending'
    """
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME).select("*").eq("analysis_status", "pending").limit(limit).execute()
    )

    return [PostDB.model_validate(row) for row in response.data]


def get_failed_posts(limit: int = 100) -> List[PostDB]:
    """Get posts that failed during LLM analysis.

    Args:
        limit: Maximum number of posts to return

    Returns:
        List of PostDB with analysis_status='failed'
    """
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME).select("*").eq("analysis_status", "failed").limit(limit).execute()
    )

    return [PostDB.model_validate(row) for row in response.data]


def get_posts_by_ids(post_ids: List[int]) -> List[PostDB]:
    """Get multiple posts by their database IDs.

    Args:
        post_ids: List of database IDs

    Returns:
        List of PostDB objects
    """
    if not post_ids:
        return []

    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").in_("id", post_ids).execute()

    return [PostDB.model_validate(row) for row in response.data]


def update_post_analysis(post_id: int, update: PostUpdate) -> Optional[PostDB]:
    """Update post analysis fields.

    Args:
        post_id: Database ID of the post
        update: Fields to update

    Returns:
        Updated PostDB if found, None otherwise
    """
    client = get_supabase_client()
    payload = update.model_dump(mode="json", exclude_none=True)

    response = client.table(TABLE_NAME).update(payload).eq("id", post_id).execute()

    if not response.data:
        return None

    return cast(PostDB, PostDB.model_validate(response.data[0]))


def mark_posts_analyzed(
    post_ids: List[int],
    status: str = "completed",
    vacancies_counts: Optional[dict[int, int]] = None,
) -> int:
    """Mark multiple posts as analyzed.

    Args:
        post_ids: List of post IDs to update
        status: New analysis status
        vacancies_counts: Optional dict mapping post_id to vacancies_count

    Returns:
        Number of posts updated
    """
    if not post_ids:
        return 0

    from datetime import datetime, timezone

    client = get_supabase_client()
    updated = 0

    for post_id in post_ids:
        payload: dict[str, Any] = {"analysis_status": status}

        # Only set analyzed_at for completed/failed status, not for pending
        if status != "pending":
            payload["analyzed_at"] = datetime.now(timezone.utc).isoformat()

        if vacancies_counts and post_id in vacancies_counts:
            payload["vacancies_count"] = vacancies_counts[post_id]

        response = client.table(TABLE_NAME).update(payload).eq("id", post_id).execute()
        if response.data:
            updated += 1

    return updated
