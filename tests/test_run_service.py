"""Tests for RunService orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Coroutine
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from job_finder.bot_control import RunResult
from job_finder.db.models import RunDB
from job_finder.run_service import RunInProgressError, RunService
from job_finder.utils.locks import PipelineLock


@pytest.mark.asyncio
async def test_start_background_run_creates_run_and_task() -> None:
    run = RunDB(
        id=10,
        status="running",
        digest_md=None,
        error=None,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        created_at=datetime.now(timezone.utc),
    )
    pipeline = AsyncMock(return_value=RunResult(message="ok", is_markdown=True, success=True))

    def _fake_task(coro: Coroutine[Any, Any, Any]) -> MagicMock:
        coro.close()
        return MagicMock()

    with (
        patch("job_finder.run_service.get_running_run", return_value=None),
        patch("job_finder.run_service.create_run", return_value=run),
        patch("job_finder.run_service.asyncio.create_task", side_effect=_fake_task) as create_task,
        patch("job_finder.run_service.update_run", return_value=run),
    ):
        service = RunService(pipeline, PipelineLock())
        result = await service.start_background_run()

    assert result.id == 10
    create_task.assert_called_once()


@pytest.mark.asyncio
async def test_start_background_run_blocks_when_running() -> None:
    run = RunDB(
        id=11,
        status="running",
        digest_md=None,
        error=None,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        created_at=datetime.now(timezone.utc),
    )
    pipeline = AsyncMock(return_value=RunResult(message="ok", is_markdown=True, success=True))

    with patch("job_finder.run_service.get_running_run", return_value=run):
        service = RunService(pipeline, PipelineLock())
        with pytest.raises(RunInProgressError):
            await service.start_background_run()


@pytest.mark.asyncio
async def test_run_and_wait_updates_status() -> None:
    run = RunDB(
        id=12,
        status="running",
        digest_md=None,
        error=None,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        created_at=datetime.now(timezone.utc),
    )
    pipeline = AsyncMock(return_value=RunResult(message="done", is_markdown=True, success=True))

    with (
        patch("job_finder.run_service.get_running_run", return_value=None),
        patch("job_finder.run_service.create_run", return_value=run),
        patch("job_finder.run_service.update_run", return_value=run) as update_run,
    ):
        service = RunService(pipeline, PipelineLock())
        result = await service.run_and_wait()

    assert result.message == "done"
    update_run.assert_called_once()


@pytest.mark.asyncio
async def test_run_and_wait_marks_failed_on_exception() -> None:
    run = RunDB(
        id=13,
        status="running",
        digest_md=None,
        error=None,
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        created_at=datetime.now(timezone.utc),
    )

    async def failing_pipeline(_: None = None) -> RunResult:
        raise RuntimeError("boom")

    with (
        patch("job_finder.run_service.get_running_run", return_value=None),
        patch("job_finder.run_service.create_run", return_value=run),
        patch("job_finder.run_service.update_run", return_value=run) as update_run,
    ):
        service = RunService(failing_pipeline, PipelineLock())
        with pytest.raises(RuntimeError):
            await service.run_and_wait()

    update_run.assert_called_once()
    payload = update_run.call_args[0][1]
    assert payload.status == "failed"
    assert payload.error == "boom"
