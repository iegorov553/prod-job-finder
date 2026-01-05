from __future__ import annotations

import asyncio
import io
import logging
import os
from dataclasses import dataclass
from functools import partial
from typing import Awaitable, Callable, List, Optional

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from job_finder.settings import SchedulerConfig, Settings, load_settings, save_settings

logger = logging.getLogger(__name__)


async def _unauthorized_reply(update: Update) -> None:
    if update.effective_chat:
        await update.effective_chat.send_message("Access denied.")


@dataclass
class RunResult:
    message: str
    log_path: Optional[str] = None


class BotController:
    def __init__(
        self,
        token: str,
        allowed_users: List[int],
        settings_path,
        on_run: Callable[[], Awaitable[RunResult]],
        on_run_preview: Callable[[], Awaitable[RunResult]],
        on_schedule_update: Callable[[SchedulerConfig], Awaitable[str]],
        get_status: Callable[[], str],
        get_digest: Callable[[], str],
        get_history: Callable[[], str],
        history_file: str | None = None,
    ):
        self.allowed_users = allowed_users
        self.settings_path = settings_path
        self.on_run = on_run
        self.on_run_preview = on_run_preview
        self.on_schedule_update = on_schedule_update
        self.get_status = get_status
        self.get_digest = get_digest
        self.get_history = get_history
        self.history_file = history_file
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
        self.app.add_handler(CommandHandler("run_once", self.handle_run_once))
        self.app.add_handler(CommandHandler("digest", self.handle_digest))
        self.app.add_handler(CommandHandler("history", self.handle_history))
        self.app.add_handler(CommandHandler("schedule", self.handle_schedule))
        self.app.add_handler(CommandHandler("schedule_set", self.handle_schedule_set))
        self.app.add_handler(CommandHandler("schedule_off", self.handle_schedule_off))

    async def _ensure_access(self, update: Update) -> bool:
        if not self._is_allowed(update):
            await _unauthorized_reply(update)
            return False
        return True

    async def _send_text_or_file(self, chat, text: str, filename: str, caption: str) -> None:
        if len(text) <= 3500:
            await chat.send_message(text)
            return
        with io.BytesIO(text.encode("utf-8")) as fh:
            fh.name = filename
            await chat.send_document(document=fh, filename=filename, caption=caption)

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
            "/run_once - тестовый сбор (до 5 постов, без обновления состояния)\n"
            "/history - последние сохранённые релевантные вакансии\n"
            "/digest - показать последний дайджест\n"
            "/schedule - показать расписание\n"
            "/schedule_set HH:MM - ежедневный запуск по UTC\n"
            "/schedule_off - выключить автозапуск"
        )
        await update.effective_chat.send_message(text)

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        await self._send_text_or_file(
            update.effective_chat,
            self.get_status(),
            "status.txt",
            "Статус",
        )

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
        await update.effective_chat.send_message(result.message)
        if result.log_path:
            try:
                size = os.path.getsize(result.log_path)
                if size <= 20 * 1024 * 1024:
                    with open(result.log_path, "rb") as fh:
                        await update.effective_chat.send_document(
                            document=fh,
                            filename=os.path.basename(result.log_path),
                            caption="Лог LLM",
                        )
                else:
                    await update.effective_chat.send_message("Лог LLM >20MB, не отправлен.")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось отправить лог: %s", exc)
            try:
                os.remove(result.log_path)
            except OSError:
                pass

    async def handle_run_once(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        await update.effective_chat.send_message("Запускаю тестовый сбор (до 5 постов)...")
        try:
            result = await self.on_run_preview()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка тестового запуска: %s", exc)
            await update.effective_chat.send_message(f"Ошибка: {exc}")
            return
        await update.effective_chat.send_message(result.message)
        if result.log_path:
            try:
                size = os.path.getsize(result.log_path)
                if size <= 20 * 1024 * 1024:
                    with open(result.log_path, "rb") as fh:
                        await update.effective_chat.send_document(
                            document=fh,
                            filename=os.path.basename(result.log_path),
                            caption="Лог LLM",
                        )
                else:
                    await update.effective_chat.send_message("Лог LLM >20MB, не отправлен.")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось отправить лог: %s", exc)
            try:
                os.remove(result.log_path)
            except OSError:
                pass

    async def handle_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        digest_text = self.get_digest() or "Дайджестов пока нет."
        await self._send_text_or_file(
            update.effective_chat,
            digest_text,
            "digest.md",
            "Дайджест",
        )

    async def handle_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        text = self.get_history() or "История пуста."
        await self._send_text_or_file(
            update.effective_chat,
            text,
            "history.txt",
            "История",
        )
        if self.history_file:
            try:
                size = os.path.getsize(self.history_file)
                if size <= 20 * 1024 * 1024:
                    with open(self.history_file, "rb") as fh:
                        await update.effective_chat.send_document(
                            document=fh,
                            filename=os.path.basename(self.history_file),
                            caption="История релевантных вакансий",
                        )
                else:
                    await update.effective_chat.send_message("История >20MB, не отправлена.")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось отправить историю: %s", exc)

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
        # Keep running until cancelled externally
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass

    async def shutdown(self) -> None:
        try:
            await self.app.updater.stop()
            await self.app.stop()
        finally:
            await self.app.shutdown()
