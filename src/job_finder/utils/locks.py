from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator


class PipelineLock:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[None]:
        await self._lock.acquire()
        try:
            yield
        finally:
            self._lock.release()

    def locked(self) -> bool:
        return self._lock.locked()
