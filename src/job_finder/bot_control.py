from __future__ import annotations

import asyncio
import io
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Awaitable, Callable, List, Optional

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from job_finder.resources import messages as msg
from job_finder.scheduler import SchedulerConfig

if TYPE_CHECKING:
    from job_finder.settings_manager import SettingsManager

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
        on_run: Callable[[Callable[[int, int], None]], Awaitable[RunResult]],
        on_run_preview: Callable[[Callable[[int, int], None]], Awaitable[RunResult]],
        on_schedule_update: Callable[[SchedulerConfig], Awaitable[str]],
        get_status: Callable[[], str],
        get_digest: Callable[[], str],
        get_history: Callable[[], str],
        history_file: str | None = None,
        settings_manager: Optional["SettingsManager"] = None,
    ):
        self.allowed_users = allowed_users
        self.on_run = on_run
        self.on_run_preview = on_run_preview
        self.on_schedule_update = on_schedule_update
        self.get_status = get_status
        self.get_digest = get_digest
        self.get_history = get_history
        self.history_file = history_file
        self.settings_manager = settings_manager
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
        # LLM settings commands
        self.app.add_handler(CommandHandler("llm", self.handle_llm))
        self.app.add_handler(CommandHandler("llm_model", self.handle_llm_model))
        self.app.add_handler(CommandHandler("llm_temp", self.handle_llm_temp))
        self.app.add_handler(CommandHandler("llm_timeout", self.handle_llm_timeout))
        self.app.add_handler(CommandHandler("llm_batch", self.handle_llm_batch))
        self.app.add_handler(CommandHandler("llm_limit", self.handle_llm_limit))
        self.app.add_handler(CommandHandler("llm_lookback", self.handle_llm_lookback))
        # Prompt commands
        self.app.add_handler(CommandHandler("prompt", self.handle_prompt))
        self.app.add_handler(CommandHandler("prompt_set", self.handle_prompt_set))
        self.app.add_handler(CommandHandler("prompt_reset", self.handle_prompt_reset))

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
            "/schedule_off - выключить автозапуск\n\n"
            "*LLM настройки:*\n"
            "/llm - показать текущие настройки\n"
            "/llm_model <name> - изменить модель\n"
            "/llm_temp <0.0-2.0> - изменить temperature\n"
            "/llm_timeout <10-300> - изменить timeout\n"
            "/llm_batch <1-50> - изменить batch size\n"
            "/llm_limit <1-500> - изменить run limit\n"
            "/llm_lookback <1-168> - изменить hours lookback\n\n"
            "*Промпт:*\n"
            "/prompt - показать текущий промпт\n"
            "/prompt_set <text> - установить промпт\n"
            "/prompt_reset - сбросить к дефолтному"
        )
        await update.effective_chat.send_message(text, parse_mode="Markdown")

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
        if not self.settings_manager:
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return
        channels = self.settings_manager.get_channels()
        if not channels:
            await update.effective_chat.send_message("Каналов нет.")
            return
        await update.effective_chat.send_message("Каналы:\n" + "\n".join(channels))

    async def handle_channels_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        if not self.settings_manager:
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return
        if not context.args:
            await update.effective_chat.send_message("Укажите каналы через пробел.")
            return
        try:
            from job_finder.db.settings import add_channels

            add_channels(list(context.args))
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message("Добавлены:\n" + "\n".join(context.args))
        except Exception as e:
            logger.exception("Failed to add channels")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_channels_remove(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not await self._ensure_access(update):
            return
        if not self.settings_manager:
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return
        if not context.args:
            await update.effective_chat.send_message("Укажите каналы через пробел.")
            return
        try:
            from job_finder.db.settings import remove_channels

            remove_channels(list(context.args))
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message("Удалены:\n" + "\n".join(context.args))
        except Exception as e:
            logger.exception("Failed to remove channels")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        await update.effective_chat.send_message("Запускаю сбор...")
        last_report = {"count": 0}

        def progress_cb(done: int, total: int) -> None:
            if done == last_report["count"]:
                return
            last_report["count"] = done
            asyncio.create_task(update.effective_chat.send_message(f"Идёт сбор: {done}/{total}"))

        try:
            result = await self.on_run(progress_cb)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка ручного запуска: %s", exc)
            await update.effective_chat.send_message(f"Ошибка: {exc}")
            return
        await self._send_text_or_file(
            update.effective_chat,
            result.message,
            "result.txt",
            "Результаты сбора",
        )
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
        last_report = {"count": 0}

        def progress_cb(done: int, total: int) -> None:
            if done == last_report["count"]:
                return
            last_report["count"] = done
            asyncio.create_task(update.effective_chat.send_message(f"Идёт сбор: {done}/{total}"))

        try:
            result = await self.on_run_preview(progress_cb)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка тестового запуска: %s", exc)
            await update.effective_chat.send_message(f"Ошибка: {exc}")
            return
        await self._send_text_or_file(
            update.effective_chat,
            result.message,
            "result.txt",
            "Результаты тестового сбора",
        )
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
        if not self.settings_manager:
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return
        scheduler_config = self.settings_manager.get_scheduler_config()
        if scheduler_config["enabled"] and scheduler_config["time_utc"]:
            await update.effective_chat.send_message(
                f"Расписание: ежедневно в {scheduler_config['time_utc']} UTC"
            )
        else:
            await update.effective_chat.send_message("Автозапуск выключен.")

    async def handle_schedule_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        if not self.settings_manager:
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return
        if not context.args:
            await update.effective_chat.send_message("Укажите время HH:MM UTC.")
            return
        time_value = context.args[0]
        try:
            from job_finder.db.settings import set_scheduler

            set_scheduler(enabled=True, time_utc=time_value)
            self.settings_manager.invalidate_cache()
            scheduler_cfg = SchedulerConfig(enabled=True, time_utc=time_value)
            reply = await self.on_schedule_update(scheduler_cfg)
            await update.effective_chat.send_message(reply)
        except Exception as e:
            logger.exception("Failed to set scheduler")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_schedule_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not await self._ensure_access(update):
            return
        if not self.settings_manager:
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return
        try:
            from job_finder.db.settings import set_scheduler

            set_scheduler(enabled=False, time_utc=None)
            self.settings_manager.invalidate_cache()
            scheduler_cfg = SchedulerConfig(enabled=False, time_utc=None)
            reply = await self.on_schedule_update(scheduler_cfg)
            await update.effective_chat.send_message(reply)
        except Exception as e:
            logger.exception("Failed to disable scheduler")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    # --- LLM Settings Commands ---

    async def handle_llm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current LLM settings."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        llm_config = self.settings_manager.get_llm_config()
        limits = self.settings_manager.get_processing_limits()

        lines = [
            msg.LLM_SETTINGS_HEADER,
            msg.LLM_SETTINGS_MODEL.format(model=llm_config["model_name"]),
        ]

        if llm_config["temperature"] is not None:
            lines.append(msg.LLM_SETTINGS_TEMPERATURE.format(temperature=llm_config["temperature"]))
        else:
            lines.append(msg.LLM_SETTINGS_TEMPERATURE_DEFAULT)

        lines.extend(
            [
                msg.LLM_SETTINGS_TIMEOUT.format(timeout=llm_config["timeout"]),
                msg.LLM_SETTINGS_RETRY_MAX.format(retry_max=llm_config["retry_max"]),
                msg.LLM_SETTINGS_RETRY_BACKOFF.format(retry_backoff=llm_config["retry_backoff"]),
                "",
                msg.LLM_SETTINGS_BATCH.format(batch=limits["max_posts_per_batch"]),
                msg.LLM_SETTINGS_LIMIT.format(limit=limits["max_posts_per_run"]),
                msg.LLM_SETTINGS_LOOKBACK.format(lookback=limits["hours_lookback"]),
            ]
        )

        await update.effective_chat.send_message("\n".join(lines), parse_mode="Markdown")

    async def handle_llm_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change LLM model name."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await update.effective_chat.send_message(msg.LLM_MODEL_USAGE, parse_mode="Markdown")
            return

        model_name = context.args[0]
        try:
            from job_finder.db.settings import update_settings_field

            update_settings_field("llm_model_name", model_name)
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(
                msg.LLM_MODEL_UPDATED.format(model=model_name),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.exception("Failed to update llm_model_name")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_temp(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change LLM temperature."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await update.effective_chat.send_message(msg.LLM_TEMP_USAGE, parse_mode="Markdown")
            return

        value_str = context.args[0].lower()

        try:
            from job_finder.db.settings import update_settings_field

            if value_str in ("none", "default", "reset"):
                update_settings_field("llm_temperature", None)
                self.settings_manager.invalidate_cache()
                await update.effective_chat.send_message(msg.LLM_TEMP_RESET)
                return

            temperature = Decimal(value_str)
            if temperature < 0 or temperature > 2:
                await update.effective_chat.send_message(msg.LLM_TEMP_INVALID)
                return

            update_settings_field("llm_temperature", float(temperature))
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(
                msg.LLM_TEMP_UPDATED.format(temperature=temperature),
                parse_mode="Markdown",
            )
        except InvalidOperation:
            await update.effective_chat.send_message(msg.LLM_TEMP_INVALID)
        except Exception as e:
            logger.exception("Failed to update llm_temperature")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_timeout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change LLM timeout."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await update.effective_chat.send_message(msg.LLM_TIMEOUT_USAGE, parse_mode="Markdown")
            return

        try:
            timeout = int(context.args[0])
            if timeout < 10 or timeout > 300:
                await update.effective_chat.send_message(msg.LLM_TIMEOUT_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("llm_timeout", timeout)
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(
                msg.LLM_TIMEOUT_UPDATED.format(timeout=timeout),
                parse_mode="Markdown",
            )
        except ValueError:
            await update.effective_chat.send_message(msg.LLM_TIMEOUT_INVALID)
        except Exception as e:
            logger.exception("Failed to update llm_timeout")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_batch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change max_posts_per_batch."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await update.effective_chat.send_message(msg.LLM_BATCH_USAGE, parse_mode="Markdown")
            return

        try:
            batch_size = int(context.args[0])
            if batch_size < 1 or batch_size > 50:
                await update.effective_chat.send_message(msg.LLM_BATCH_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("max_posts_per_batch", batch_size)
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(
                msg.LLM_BATCH_UPDATED.format(batch=batch_size),
                parse_mode="Markdown",
            )
        except ValueError:
            await update.effective_chat.send_message(msg.LLM_BATCH_INVALID)
        except Exception as e:
            logger.exception("Failed to update max_posts_per_batch")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change max_posts_per_run."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await update.effective_chat.send_message(msg.LLM_LIMIT_USAGE, parse_mode="Markdown")
            return

        try:
            run_limit = int(context.args[0])
            if run_limit < 1 or run_limit > 500:
                await update.effective_chat.send_message(msg.LLM_LIMIT_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("max_posts_per_run", run_limit)
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(
                msg.LLM_LIMIT_UPDATED.format(limit=run_limit),
                parse_mode="Markdown",
            )
        except ValueError:
            await update.effective_chat.send_message(msg.LLM_LIMIT_INVALID)
        except Exception as e:
            logger.exception("Failed to update max_posts_per_run")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_lookback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change hours_lookback."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await update.effective_chat.send_message(msg.LLM_LOOKBACK_USAGE, parse_mode="Markdown")
            return

        try:
            lookback = int(context.args[0])
            if lookback < 1 or lookback > 168:
                await update.effective_chat.send_message(msg.LLM_LOOKBACK_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("hours_lookback", lookback)
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(
                msg.LLM_LOOKBACK_UPDATED.format(lookback=lookback),
                parse_mode="Markdown",
            )
        except ValueError:
            await update.effective_chat.send_message(msg.LLM_LOOKBACK_INVALID)
        except Exception as e:
            logger.exception("Failed to update hours_lookback")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    # --- Prompt Commands ---

    async def handle_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current system prompt."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        custom_prompt = self.settings_manager.get_custom_prompt()

        lines = [msg.PROMPT_HEADER]
        if custom_prompt:
            # Truncate for display if too long
            display_prompt = (
                custom_prompt[:1500] + "..." if len(custom_prompt) > 1500 else custom_prompt
            )
            lines.append(msg.PROMPT_CURRENT.format(prompt=display_prompt))
        else:
            lines.append(msg.PROMPT_DEFAULT)

        await update.effective_chat.send_message("\n".join(lines), parse_mode="Markdown")

    async def handle_prompt_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set custom system prompt."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await update.effective_chat.send_message(msg.PROMPT_SET_USAGE)
            return

        # Join all args as prompt text
        prompt_text = " ".join(context.args)

        if len(prompt_text) > 10000:
            await update.effective_chat.send_message(msg.PROMPT_SET_TOO_LONG)
            return

        try:
            from job_finder.db.settings import update_settings_field

            update_settings_field("custom_prompt", prompt_text)
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(msg.PROMPT_SET_SUCCESS)
        except Exception as e:
            logger.exception("Failed to update custom_prompt")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_prompt_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reset to default system prompt."""
        if not await self._ensure_access(update):
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await update.effective_chat.send_message(msg.SETTINGS_DB_UNAVAILABLE)
            return

        try:
            from job_finder.db.settings import reset_custom_prompt

            reset_custom_prompt()
            self.settings_manager.invalidate_cache()
            await update.effective_chat.send_message(msg.PROMPT_RESET_SUCCESS)
        except Exception as e:
            logger.exception("Failed to reset custom_prompt")
            await update.effective_chat.send_message(msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

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
