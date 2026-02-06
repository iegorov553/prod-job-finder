from __future__ import annotations

import asyncio

import pytest

from job_finder.utils.locks import PipelineLock


@pytest.mark.asyncio
async def test_pipeline_lock_is_reentrant_for_same_task() -> None:
    lock = PipelineLock()

    assert not lock.locked()
    async with lock.acquire():
        assert lock.locked()
        async with lock.acquire():
            assert lock.locked()
        assert lock.locked()
    assert not lock.locked()


@pytest.mark.asyncio
async def test_pipeline_lock_blocks_other_task() -> None:
    lock = PipelineLock()
    events: list[str] = []

    async def holder() -> None:
        async with lock.acquire():
            events.append("holder_acquired")
            await asyncio.sleep(0.05)
            events.append("holder_releasing")

    async def waiter() -> None:
        await asyncio.sleep(0.01)
        events.append("waiter_waiting")
        async with lock.acquire():
            events.append("waiter_acquired")

    await asyncio.gather(holder(), waiter())

    assert events.index("waiter_waiting") < events.index("holder_releasing")
    assert events.index("holder_releasing") < events.index("waiter_acquired")
