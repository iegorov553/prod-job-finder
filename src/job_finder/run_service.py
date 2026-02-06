"""Run orchestration for pipeline executions."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from job_finder.bot_control import RunResult
from job_finder.db.models import RunDB, RunUpdate
from job_finder.db.runs import create_run, get_running_run, update_run
from job_finder.utils.locks import PipelineLock

logger = logging.getLogger(__name__)


class RunInProgressError(RuntimeError):
    """Raised when a run is already in progress."""


class RunService:
    def __init__(
        self,
        pipeline: Callable[[Callable[[int, int], None] | None], Awaitable[RunResult]],
        lock: PipelineLock,
    ) -> None:
        self._pipeline = pipeline
        self._lock = lock

    def _has_active_run(self) -> bool:
        return self._lock.locked() or get_running_run() is not None

    def has_active_run(self) -> bool:
        return self._has_active_run()

    async def start_background_run(self) -> RunDB:
        if self._has_active_run():
            raise RunInProgressError("Run already in progress")
        run = create_run()
        asyncio.create_task(self._execute_run_background(run.id))
        return run

    async def run_and_wait(
        self, progress_cb: Callable[[int, int], None] | None = None
    ) -> RunResult:
        if self._has_active_run():
            raise RunInProgressError("Run already in progress")
        run = create_run()
        return await self._execute_run(run.id, progress_cb)

    async def _execute_run(
        self,
        run_id: int,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> RunResult:
        async with self._lock.acquire():
            try:
                result = await self._pipeline(progress_cb)
                self._persist_result(run_id, result)
                return result
            except Exception as exc:  # noqa: BLE001
                logger.exception("Run failed: %s", exc)
                self._persist_failure(run_id, str(exc))
                raise

    async def _execute_run_background(self, run_id: int) -> None:
        try:
            await self._execute_run(run_id)
        except Exception:  # noqa: BLE001
            logger.info("Background run failed; error persisted.")

    def _persist_result(self, run_id: int, result: RunResult) -> None:
        finished_at = datetime.now(timezone.utc)
        if result.success:
            update = RunUpdate(
                status="success",
                digest_md=result.message,
                finished_at=finished_at,
            )
        else:
            update = RunUpdate(
                status="failed",
                error=result.message,
                finished_at=finished_at,
            )
        update_run(run_id, update)

    def _persist_failure(self, run_id: int, error: str) -> None:
        finished_at = datetime.now(timezone.utc)
        update_run(run_id, RunUpdate(status="failed", error=error, finished_at=finished_at))
