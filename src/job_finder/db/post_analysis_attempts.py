"""CRUD operations for post_analysis_attempts table."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from job_finder.db.client import get_supabase_client
from job_finder.db.models import PostAnalysisAttemptCreate

TABLE_NAME = "post_analysis_attempts"


def create_post_analysis_attempts(
    attempts: Sequence[PostAnalysisAttemptCreate | Mapping[str, Any]],
) -> int:
    """Insert post analysis attempt rows in a single batch operation."""
    if not attempts:
        return 0

    payloads: list[dict[str, Any]] = []
    for item in attempts:
        if isinstance(item, PostAnalysisAttemptCreate):
            payloads.append(item.model_dump(mode="json", exclude_none=True))
        else:
            payloads.append(dict(item))

    client = get_supabase_client()
    response = client.table(TABLE_NAME).insert(payloads).execute()
    return len(response.data)
