from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import Awaitable, Callable, List

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from job_finder.settings import SchedulerConfig, Settings, load_settings, save_settings

logger = logging.getLogger(__name__)


async def _unauthorized_reply(update: Update) -> None:
    if update.effective_chat:
        await update.effective_chat.send_message("Access denied.")


class BotController:
    def __init__(
        self,
        token: str,
        allowed_users: List[int],
        settings_path,
        on_run: Callable[[], Awaitable[str]],
        on_schedule_update: Callable[[SchedulerConfig], Awaitable[str]],
        get_status: Callable[[], str],
        get_digest: Callable[[], str],
    ):
        self.allowed_users = allowed_users
        self.settings_path = settings_path
        self.on_run = on_run
        self.on_schedule_update = on_schedule_update
        self.get_status = get_status
        self.get_digest = get_digest
        self.app: Application = ApplicationBuilder().token(token).build()
        self._register_handlers()

    def _is_allowed(self, update: Update) -> bool:
        user_id = update.effective_user.id if update.effective_user else None
        return user_id in self.allowed_users

    def _register_handlers(self) -> None:
        self.app.add_handler(CommandHandler("help", self.handle_help))
        self.app.add_handler(CommandHandler("status", self.handle_status))
        self.app.add_handler(CommandHandler("channels", self.handle_channels))
        self.app.add_handler(CommandHandler("channels_add", self.handle_channels_add))
        self.app.add_handler(CommandHandler("channels_remove", self.handle_channels_remove))
        self.app.add_handler(CommandHandler("run", self.handle_run))
        self.app.add_handler(CommandHandler("digest", self.handle_digest))
        self.app.add_handler(CommandHandler("schedule", self.handle_schedule))
        self.app.add_handler(CommandHandler("schedule_set", self.handle_schedule_set))
        self.app.add_handler(CommandHandler("schedule_off", self.handle_schedule_off))

    async def _ensure_access(self, update: Update) -> bool:
        if not self._is_allowed(update):
            await _unauthorized_reply(update)
            return False
        return True

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        text = (
            "/help - эта справка\n"
            "/status - статус каналов и расписания\n"
            "/channels - текущий список каналов\n"
            "/channels_add @a @b - добавить каналы\n"
            "/channels_remove @a - убрать каналы\n"
            "/run - запустить сбор сейчас\n"
            "/digest - показать последний дайджест\n"
            "/schedule - показать расписание\n"
            "/schedule_set HH:MM - ежедневный запуск по UTC\n"
            "/schedule_off - выключить автозапуск"
        )
        await update.effective_chat.send_message(text)

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        await update.effective_chat.send_message(self.get_status())

    async def handle_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        settings = load_settings(self.settings_path)
        if not settings.channels:
            await update.effective_chat.send_message("Каналов нет.")
            return
        await update.effective_chat.send_message("Каналы:\n" + "\n".join(settings.channels))

    async def handle_channels_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        if not context.args:
            await update.effective_chat.send_message("Укажите каналы через пробел.")
            return
        settings = load_settings(self.settings_path)
        settings.add_channels(context.args)
        save_settings(self.settings_path, settings)
        await update.effective_chat.send_message("Добавлены:\n" + "\n".join(context.args))

    async def handle_channels_remove(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        if not context.args:
            await update.effective_chat.send_message("Укажите каналы через пробел.")
            return
        settings = load_settings(self.settings_path)
        settings.remove_channels(context.args)
        save_settings(self.settings_path, settings)
        await update.effective_chat.send_message("Удалены:\n" + "\n".join(context.args))

    async def handle_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        await update.effective_chat.send_message("Запускаю сбор...")
        try:
            result = await self.on_run()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка ручного запуска: %s", exc)
            await update.effective_chat.send_message(f"Ошибка: {exc}")
            return
        await update.effective_chat.send_message(result)

    async def handle_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        await update.effective_chat.send_message(self.get_digest() or "Дайджестов пока нет.")

    async def handle_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        settings = load_settings(self.settings_path)
        if settings.scheduler.enabled and settings.scheduler.time_utc:
            await update.effective_chat.send_message(
                f"Расписание: ежедневно в {settings.scheduler.time_utc} UTC"
            )
        else:
            await update.effective_chat.send_message("Автозапуск выключен.")

    async def handle_schedule_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        if not context.args:
            await update.effective_chat.send_message("Укажите время HH:MM UTC.")
            return
        time_value = context.args[0]
        settings = load_settings(self.settings_path)
        settings.scheduler.enabled = True
        settings.scheduler.time_utc = time_value
        save_settings(self.settings_path, settings)
        msg = await self.on_schedule_update(settings.scheduler)
        await update.effective_chat.send_message(msg)

    async def handle_schedule_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        settings = load_settings(self.settings_path)
        settings.scheduler.enabled = False
        settings.scheduler.time_utc = None
        save_settings(self.settings_path, settings)
        msg = await self.on_schedule_update(settings.scheduler)
        await update.effective_chat.send_message(msg)

    async def run_polling(self) -> None:
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def shutdown(self) -> None:
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
