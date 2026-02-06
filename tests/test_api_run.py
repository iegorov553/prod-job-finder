"""Tests for run API endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi.testclient import TestClient

from job_finder.db.models import RunDB
from job_finder.run_service import RunInProgressError


class DummyRunService:
    def __init__(self, run: Optional[RunDB] = None, error: Exception | None = None) -> None:
        self._run = run
        self._error = error

    async def start_background_run(self) -> RunDB:
        if self._error:
            raise self._error
        assert self._run is not None
        return self._run


def _make_run(run_id: int) -> RunDB:
    now = datetime.now(timezone.utc)
    return RunDB(
        id=run_id,
        status="running",
        digest_md=None,
        error=None,
        started_at=now,
        finished_at=None,
        created_at=now,
    )


def test_run_requires_auth() -> None:
    from job_finder.api.app import create_app

    app = create_app(DummyRunService(run=_make_run(1)), api_token="secret")
    client = TestClient(app)

    response = client.post("/api/run")

    assert response.status_code == 401


def test_run_success() -> None:
    from job_finder.api.app import create_app

    app = create_app(DummyRunService(run=_make_run(2)), api_token="secret")
    client = TestClient(app)

    response = client.post("/api/run", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 202
    data = response.json()
    assert data["run_id"] == 2
    assert data["status"] == "running"


def test_run_conflict_when_running() -> None:
    from job_finder.api.app import create_app

    app = create_app(DummyRunService(error=RunInProgressError("busy")), api_token="secret")
    client = TestClient(app)

    response = client.post("/api/run", headers={"Authorization": "Bearer secret"})

    assert response.status_code == 409
