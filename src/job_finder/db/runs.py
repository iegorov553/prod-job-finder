"""CRUD operations for runs table."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, cast

from job_finder.db.client import get_supabase_client
from job_finder.db.models import RunCreate, RunDB, RunStatus, RunUpdate

TABLE_NAME = "runs"


def create_run(status: RunStatus = "running") -> RunDB:
    """Create a new run entry."""
    client = get_supabase_client()
    payload = RunCreate(status=status).model_dump(mode="json")
    response = client.table(TABLE_NAME).insert(payload).execute()
    return cast(RunDB, RunDB.model_validate(response.data[0]))


def get_latest_run() -> Optional[RunDB]:
    """Fetch the most recent run."""
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME).select("*").order("started_at", desc=True).limit(1).execute()
    )
    if not response.data:
        return None
    return cast(RunDB, RunDB.model_validate(response.data[0]))


def get_running_run() -> Optional[RunDB]:
    """Fetch the latest running run if any."""
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME)
        .select("*")
        .eq("status", "running")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return cast(RunDB, RunDB.model_validate(response.data[0]))


def list_runs(limit: int = 10) -> List[RunDB]:
    """List recent runs."""
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME).select("*").order("started_at", desc=True).limit(limit).execute()
    )
    return [RunDB.model_validate(row) for row in response.data]


def update_run(run_id: int, update: RunUpdate) -> Optional[RunDB]:
    """Update a run entry by ID."""
    client = get_supabase_client()
    payload = update.model_dump(mode="json", exclude_none=True)

    if not payload:
        return get_latest_run()

    response = client.table(TABLE_NAME).update(payload).eq("id", run_id).execute()
    if not response.data:
        return None
    return cast(RunDB, RunDB.model_validate(response.data[0]))


def mark_running_failed(reason: str) -> int:
    """Mark all running runs as failed with an error reason."""
    client = get_supabase_client()
    payload: dict[str, Any] = {
        "status": "failed",
        "error": reason,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    response = client.table(TABLE_NAME).update(cast(Any, payload)).eq("status", "running").execute()
    return len(response.data)
