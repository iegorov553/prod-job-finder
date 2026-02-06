from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator


class PipelineLock:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._owner: asyncio.Task[Any] | None = None
        self._depth = 0

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        current_task = asyncio.current_task()
        if current_task is not None and self._owner is current_task:
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
                if self._depth == 0:
                    self._owner = None
                    self._lock.release()
            return

        await self._lock.acquire()
        self._owner = current_task
        self._depth = 1
        try:
            yield
        finally:
            self._depth -= 1
            if self._depth == 0:
                self._owner = None
                self._lock.release()

    def locked(self) -> bool:
        return self._lock.locked()
