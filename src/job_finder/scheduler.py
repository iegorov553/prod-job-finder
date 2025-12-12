from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from job_finder.settings import SchedulerConfig

logger = logging.getLogger(__name__)

JobFunc = Callable[[], Awaitable[None]]


class PipelineScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._job_id = "daily_job"

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    def clear_job(self) -> None:
        if self._scheduler.get_job(self._job_id):
            self._scheduler.remove_job(self._job_id)

    def update(self, cfg: SchedulerConfig, func: JobFunc) -> None:
        self.clear_job()
        if not cfg.enabled or not cfg.time_utc:
            logger.info("Автозапуск выключен.")
            return
        try:
            hour, minute = [int(part) for part in cfg.time_utc.split(":")]
        except Exception:  # noqa: BLE001
            logger.warning("Некорректное время расписания: %s", cfg.time_utc)
            return
        trigger = CronTrigger(hour=hour, minute=minute, timezone="UTC")
        self._scheduler.add_job(func, trigger, id=self._job_id, replace_existing=True)
        logger.info("Запланирован автозапуск ежедневно в %02d:%02d UTC", hour, minute)
