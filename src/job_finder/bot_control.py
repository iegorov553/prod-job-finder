from __future__ import annotations

import asyncio
import io
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Awaitable, Callable, List, Optional

from telegram import Chat, LinkPreviewOptions, Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

from job_finder import telegram_markdown as mdv2
from job_finder.resources import messages as msg
from job_finder.scheduler import SchedulerConfig

if TYPE_CHECKING:
    from job_finder.settings_manager import SettingsManager

logger = logging.getLogger(__name__)
MARKDOWN_MODE = "MarkdownV2"


async def _unauthorized_reply(update: Update) -> None:
    if update.effective_chat:
        await update.effective_chat.send_message(
            mdv2.escape(msg.ACCESS_DENIED),
            parse_mode=MARKDOWN_MODE,
        )


@dataclass
class RunResult:
    message: Optional[str]
    log_path: Optional[str] = None
    is_markdown: bool = False
    success: bool = True


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
        # Retry commands
        self.app.add_handler(CommandHandler("retry_failed", self.handle_retry_failed))
        # JobSpy commands
        self.app.add_handler(CommandHandler("jobspy", self.handle_jobspy))
        self.app.add_handler(CommandHandler("jobspy_toggle", self.handle_jobspy_toggle))
        self.app.add_handler(CommandHandler("jobspy_sites", self.handle_jobspy_sites))
        self.app.add_handler(CommandHandler("jobspy_search", self.handle_jobspy_search))
        self.app.add_handler(CommandHandler("jobspy_location", self.handle_jobspy_location))
        self.app.add_handler(CommandHandler("jobspy_results", self.handle_jobspy_results))

    async def _ensure_access(self, update: Update) -> Chat | None:
        if not self._is_allowed(update):
            await _unauthorized_reply(update)
            return None
        return update.effective_chat

    async def _send_message(
        self,
        chat: Chat,
        text: str,
        *,
        formatted: bool = False,
        disable_link_preview: bool = False,
    ) -> None:
        message_text = text if formatted else mdv2.escape(text)
        link_preview = LinkPreviewOptions(is_disabled=True) if disable_link_preview else None
        await chat.send_message(
            message_text,
            parse_mode=MARKDOWN_MODE,
            link_preview_options=link_preview,
        )

    async def _send_text_or_file(
        self,
        chat: Chat,
        text: str | None,
        filename: str,
        caption: str,
        parse_mode: str | None = MARKDOWN_MODE,
        disable_link_preview: bool = False,
        formatted: bool = False,
    ) -> None:
        if text is None:
            text = msg.EMPTY_RESULT
        if parse_mode == MARKDOWN_MODE and not formatted:
            text = mdv2.escape(text)
        if len(text) <= 3500:
            link_preview = LinkPreviewOptions(is_disabled=True) if disable_link_preview else None
            await chat.send_message(
                text,
                parse_mode=parse_mode,
                link_preview_options=link_preview,
            )
            return
        # File is sent without parse_mode (markdown inside file)
        with io.BytesIO(text.encode("utf-8")) as fh:
            fh.name = filename
            await chat.send_document(document=fh, filename=filename, caption=caption)

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        lines: list[str] = []
        lines.extend(mdv2.escape(line) for line in msg.HELP_GENERAL)
        lines.append("")
        lines.append(mdv2.bold(msg.HELP_LLM_HEADER))
        lines.extend(mdv2.escape(line) for line in msg.HELP_LLM)
        lines.append("")
        lines.append(mdv2.bold(msg.HELP_PROMPT_HEADER))
        lines.extend(mdv2.escape(line) for line in msg.HELP_PROMPT)
        lines.append("")
        lines.append(mdv2.bold(msg.HELP_JOBSPY_HEADER))
        lines.extend(mdv2.escape(line) for line in msg.HELP_JOBSPY)
        await self._send_message(chat, "\n".join(lines), formatted=True)

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        await self._send_text_or_file(
            chat,
            self.get_status(),
            "status.txt",
            "Статус",
        )

    async def handle_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager:
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return
        channels = self.settings_manager.get_channels()
        if not channels:
            await self._send_message(chat, "Каналов нет.")
            return
        await self._send_message(chat, "Каналы:\n" + "\n".join(channels))

    async def handle_channels_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager:
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return
        if not context.args:
            await self._send_message(chat, "Укажите каналы через пробел.")
            return
        try:
            from job_finder.db.settings import add_channels

            add_channels(list(context.args))
            self.settings_manager.invalidate_cache()
            await self._send_message(chat, "Добавлены:\n" + "\n".join(context.args))
        except Exception as e:
            logger.exception("Failed to add channels")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_channels_remove(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager:
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return
        if not context.args:
            await self._send_message(chat, "Укажите каналы через пробел.")
            return
        try:
            from job_finder.db.settings import remove_channels

            remove_channels(list(context.args))
            self.settings_manager.invalidate_cache()
            await self._send_message(chat, "Удалены:\n" + "\n".join(context.args))
        except Exception as e:
            logger.exception("Failed to remove channels")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_run(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        await self._send_message(chat, "Запускаю сбор...")
        last_report = {"count": 0}

        def progress_cb(done: int, total: int) -> None:
            if done == last_report["count"]:
                return
            last_report["count"] = done
            asyncio.create_task(self._send_message(chat, f"Идёт сбор: {done}/{total}"))

        try:
            result = await self.on_run(progress_cb)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка ручного запуска: %s", exc)
            await self._send_message(chat, f"Ошибка: {exc}")
            return
        await self._send_text_or_file(
            chat,
            result.message,
            "result.txt",
            "Результаты сбора",
            formatted=result.is_markdown,
            disable_link_preview=True,
        )
        if result.log_path:
            try:
                size = os.path.getsize(result.log_path)
                if size <= 20 * 1024 * 1024:
                    with open(result.log_path, "rb") as fh:
                        await chat.send_document(
                            document=fh,
                            filename=os.path.basename(result.log_path),
                            caption="Лог LLM",
                        )
                else:
                    await self._send_message(chat, "Лог LLM >20MB, не отправлен.")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось отправить лог: %s", exc)
            try:
                os.remove(result.log_path)
            except OSError:
                pass

    async def handle_run_once(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        await self._send_message(chat, "Запускаю тестовый сбор (до 5 постов)...")
        last_report = {"count": 0}

        def progress_cb(done: int, total: int) -> None:
            if done == last_report["count"]:
                return
            last_report["count"] = done
            asyncio.create_task(self._send_message(chat, f"Идёт сбор: {done}/{total}"))

        try:
            result = await self.on_run_preview(progress_cb)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка тестового запуска: %s", exc)
            await self._send_message(chat, f"Ошибка: {exc}")
            return
        await self._send_text_or_file(
            chat,
            result.message,
            "result.txt",
            "Результаты тестового сбора",
            formatted=result.is_markdown,
            disable_link_preview=True,
        )
        if result.log_path:
            try:
                size = os.path.getsize(result.log_path)
                if size <= 20 * 1024 * 1024:
                    with open(result.log_path, "rb") as fh:
                        await chat.send_document(
                            document=fh,
                            filename=os.path.basename(result.log_path),
                            caption="Лог LLM",
                        )
                else:
                    await self._send_message(chat, "Лог LLM >20MB, не отправлен.")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось отправить лог: %s", exc)
            try:
                os.remove(result.log_path)
            except OSError:
                pass

    async def handle_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        digest_text = self.get_digest()
        has_digest = bool(digest_text)
        if not digest_text:
            digest_text = msg.DIGEST_NOT_FOUND
        await self._send_text_or_file(
            chat,
            digest_text,
            "digest.md",
            "Дайджест",
            formatted=has_digest,
            disable_link_preview=True,
        )

    async def handle_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        text = self.get_history() or msg.HISTORY_EMPTY
        await self._send_text_or_file(
            chat,
            text,
            "history.txt",
            "История",
        )
        if self.history_file:
            try:
                size = os.path.getsize(self.history_file)
                if size <= 20 * 1024 * 1024:
                    with open(self.history_file, "rb") as fh:
                        await chat.send_document(
                            document=fh,
                            filename=os.path.basename(self.history_file),
                            caption="История релевантных вакансий",
                        )
                else:
                    await self._send_message(chat, "История >20MB, не отправлена.")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Не удалось отправить историю: %s", exc)

    async def handle_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager:
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return
        scheduler_config = self.settings_manager.get_scheduler_config()
        if scheduler_config["enabled"] and scheduler_config["time_utc"]:
            await self._send_message(
                chat,
                f"Расписание: ежедневно в {scheduler_config['time_utc']} UTC",
            )
        else:
            await self._send_message(chat, "Автозапуск выключен.")

    async def handle_schedule_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager:
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return
        if not context.args:
            await self._send_message(chat, "Укажите время HH:MM UTC.")
            return
        time_value = context.args[0]
        try:
            from job_finder.db.settings import set_scheduler

            set_scheduler(enabled=True, time_utc=time_value)
            self.settings_manager.invalidate_cache()
            scheduler_cfg = SchedulerConfig(enabled=True, time_utc=time_value)
            reply = await self.on_schedule_update(scheduler_cfg)
            await self._send_message(chat, reply)
        except Exception as e:
            logger.exception("Failed to set scheduler")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_schedule_off(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager:
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return
        try:
            from job_finder.db.settings import set_scheduler

            set_scheduler(enabled=False, time_utc=None)
            self.settings_manager.invalidate_cache()
            scheduler_cfg = SchedulerConfig(enabled=False, time_utc=None)
            reply = await self.on_schedule_update(scheduler_cfg)
            await self._send_message(chat, reply)
        except Exception as e:
            logger.exception("Failed to disable scheduler")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    # --- LLM Settings Commands ---

    async def handle_llm(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current LLM settings."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        llm_config = self.settings_manager.get_llm_config()
        limits = self.settings_manager.get_processing_limits()

        lines = [
            mdv2.bold(msg.LLM_SETTINGS_HEADER),
            f"{mdv2.escape(msg.LLM_SETTINGS_MODEL)}: {mdv2.code(str(llm_config['model_name']))}",
        ]

        if llm_config["temperature"] is not None:
            lines.append(
                f"{mdv2.escape(msg.LLM_SETTINGS_TEMPERATURE)}: "
                f"{mdv2.code(str(llm_config['temperature']))}"
            )
        else:
            lines.append(
                f"{mdv2.escape(msg.LLM_SETTINGS_TEMPERATURE)}: "
                f"{mdv2.italic(msg.LLM_SETTINGS_TEMPERATURE_DEFAULT)}"
            )

        lines.extend(
            [
                f"{mdv2.escape(msg.LLM_SETTINGS_TIMEOUT)}: "
                f"{mdv2.code(str(llm_config['timeout']))} сек",
                f"{mdv2.escape(msg.LLM_SETTINGS_RETRY_MAX)}: "
                f"{mdv2.code(str(llm_config['retry_max']))}",
                f"{mdv2.escape(msg.LLM_SETTINGS_RETRY_BACKOFF)}: "
                f"{mdv2.code(str(llm_config['retry_backoff']))}",
                "",
                f"{mdv2.escape(msg.LLM_SETTINGS_BATCH)}: "
                f"{mdv2.code(str(limits['max_posts_per_batch']))}",
                f"{mdv2.escape(msg.LLM_SETTINGS_LIMIT)}: "
                f"{mdv2.code(str(limits['max_posts_per_run']))}",
                f"{mdv2.escape(msg.LLM_SETTINGS_LOOKBACK)}: "
                f"{mdv2.code(str(limits['hours_lookback']))}",
            ]
        )

        await self._send_message(chat, "\n".join(lines), formatted=True)

    async def handle_llm_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change LLM model name."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.LLM_MODEL_USAGE)
            return

        model_name = context.args[0]
        try:
            from job_finder.db.settings import update_settings_field

            update_settings_field("llm_model_name", model_name)
            self.settings_manager.invalidate_cache()
            await self._send_message(
                chat,
                msg.LLM_MODEL_UPDATED.format(model=mdv2.code(model_name)),
                formatted=True,
            )
        except Exception as e:
            logger.exception("Failed to update llm_model_name")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_temp(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change LLM temperature."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.LLM_TEMP_USAGE)
            return

        value_str = context.args[0].lower()

        try:
            from job_finder.db.settings import update_settings_field

            if value_str in ("none", "default", "reset"):
                update_settings_field("llm_temperature", None)
                self.settings_manager.invalidate_cache()
                await self._send_message(chat, msg.LLM_TEMP_RESET)
                return

            temperature = Decimal(value_str)
            if temperature < 0 or temperature > 2:
                await self._send_message(chat, msg.LLM_TEMP_INVALID)
                return

            update_settings_field("llm_temperature", float(temperature))
            self.settings_manager.invalidate_cache()
            await self._send_message(
                chat,
                msg.LLM_TEMP_UPDATED.format(temperature=mdv2.code(str(temperature))),
                formatted=True,
            )
        except InvalidOperation:
            await self._send_message(chat, msg.LLM_TEMP_INVALID)
        except Exception as e:
            logger.exception("Failed to update llm_temperature")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_timeout(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change LLM timeout."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.LLM_TIMEOUT_USAGE)
            return

        try:
            timeout = int(context.args[0])
            if timeout < 10 or timeout > 300:
                await self._send_message(chat, msg.LLM_TIMEOUT_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("llm_timeout", timeout)
            self.settings_manager.invalidate_cache()
            await self._send_message(
                chat,
                msg.LLM_TIMEOUT_UPDATED.format(timeout=mdv2.code(str(timeout))),
                formatted=True,
            )
        except ValueError:
            await self._send_message(chat, msg.LLM_TIMEOUT_INVALID)
        except Exception as e:
            logger.exception("Failed to update llm_timeout")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_batch(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change max_posts_per_batch."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.LLM_BATCH_USAGE)
            return

        try:
            batch_size = int(context.args[0])
            if batch_size < 1 or batch_size > 50:
                await self._send_message(chat, msg.LLM_BATCH_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("max_posts_per_batch", batch_size)
            self.settings_manager.invalidate_cache()
            await self._send_message(
                chat,
                msg.LLM_BATCH_UPDATED.format(batch=mdv2.code(str(batch_size))),
                formatted=True,
            )
        except ValueError:
            await self._send_message(chat, msg.LLM_BATCH_INVALID)
        except Exception as e:
            logger.exception("Failed to update max_posts_per_batch")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change max_posts_per_run."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.LLM_LIMIT_USAGE)
            return

        try:
            run_limit = int(context.args[0])
            if run_limit < 1 or run_limit > 500:
                await self._send_message(chat, msg.LLM_LIMIT_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("max_posts_per_run", run_limit)
            self.settings_manager.invalidate_cache()
            await self._send_message(
                chat,
                msg.LLM_LIMIT_UPDATED.format(limit=mdv2.code(str(run_limit))),
                formatted=True,
            )
        except ValueError:
            await self._send_message(chat, msg.LLM_LIMIT_INVALID)
        except Exception as e:
            logger.exception("Failed to update max_posts_per_run")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_llm_lookback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Change hours_lookback."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.LLM_LOOKBACK_USAGE)
            return

        try:
            lookback = int(context.args[0])
            if lookback < 1 or lookback > 168:
                await self._send_message(chat, msg.LLM_LOOKBACK_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("hours_lookback", lookback)
            self.settings_manager.invalidate_cache()
            await self._send_message(
                chat,
                msg.LLM_LOOKBACK_UPDATED.format(lookback=mdv2.code(str(lookback))),
                formatted=True,
            )
        except ValueError:
            await self._send_message(chat, msg.LLM_LOOKBACK_INVALID)
        except Exception as e:
            logger.exception("Failed to update hours_lookback")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    # --- Prompt Commands ---

    async def handle_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current system prompt."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        custom_prompt = self.settings_manager.get_custom_prompt()

        lines = [mdv2.bold(msg.PROMPT_HEADER)]
        if custom_prompt:
            # Truncate for display if too long
            display_prompt = (
                custom_prompt[:1500] + "..." if len(custom_prompt) > 1500 else custom_prompt
            )
            lines.append(mdv2.pre(display_prompt))
        else:
            lines.append(mdv2.italic(msg.PROMPT_DEFAULT))

        await self._send_message(chat, "\n".join(lines), formatted=True)

    async def handle_prompt_set(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set custom system prompt."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.PROMPT_SET_USAGE)
            return

        # Join all args as prompt text
        prompt_text = " ".join(context.args)

        if len(prompt_text) > 10000:
            await self._send_message(chat, msg.PROMPT_SET_TOO_LONG)
            return

        try:
            from job_finder.db.settings import update_settings_field

            update_settings_field("custom_prompt", prompt_text)
            self.settings_manager.invalidate_cache()
            await self._send_message(chat, msg.PROMPT_SET_SUCCESS)
        except Exception as e:
            logger.exception("Failed to update custom_prompt")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_prompt_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Reset to default system prompt."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        try:
            from job_finder.db.settings import reset_custom_prompt

            reset_custom_prompt()
            self.settings_manager.invalidate_cache()
            await self._send_message(chat, msg.PROMPT_RESET_SUCCESS)
        except Exception as e:
            logger.exception("Failed to reset custom_prompt")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_retry_failed(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Retry analysis of failed posts."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        # Parse limit from args (default 30)
        limit = 30
        if context.args:
            try:
                limit = int(context.args[0])
                if limit < 1 or limit > 500:
                    await self._send_message(chat, msg.RETRY_FAILED_INVALID_LIMIT)
                    return
            except ValueError:
                await self._send_message(chat, msg.RETRY_FAILED_INVALID_LIMIT)
                return

        # Get failed posts from DB
        from job_finder.db.posts import get_failed_posts

        failed_posts = get_failed_posts(limit=limit)

        if not failed_posts:
            await self._send_message(chat, msg.RETRY_FAILED_NO_POSTS)
            return

        await self._send_message(
            chat,
            msg.RETRY_FAILED_START.format(count=len(failed_posts)),
        )

        # Reset status to pending for retry
        from job_finder.db.posts import mark_posts_analyzed

        post_ids = [p.id for p in failed_posts]
        mark_posts_analyzed(post_ids, status="pending", vacancies_counts=None)

        # Trigger analysis via on_run callback
        last_report = {"count": 0}

        def progress_cb(done: int, total: int) -> None:
            if done == last_report["count"]:
                return
            last_report["count"] = done
            progress_msg = msg.RETRY_FAILED_PROGRESS.format(done=done, total=total)
            asyncio.create_task(self._send_message(chat, progress_msg))

        try:
            result = await self.on_run(progress_cb)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Retry failed posts error: %s", exc)
            await self._send_message(chat, msg.RETRY_FAILED_ERROR.format(error=str(exc)))
            return

        await self._send_text_or_file(
            chat,
            result.message,
            "retry_result.txt",
            msg.RETRY_FAILED_RESULT,
            formatted=result.is_markdown,
            disable_link_preview=True,
        )

    # --- JobSpy Commands ---

    async def handle_jobspy(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current JobSpy settings."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        settings = self.settings_manager.get_settings()
        if not settings:
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if settings.jobspy_enabled:
            enabled_text = msg.JOBSPY_SETTINGS_ENABLED_ON
        else:
            enabled_text = msg.JOBSPY_SETTINGS_ENABLED_OFF
        location_text = settings.jobspy_location or msg.JOBSPY_SETTINGS_LOCATION_NOT_SET
        job_type_text = settings.jobspy_job_type or msg.JOBSPY_SETTINGS_JOB_TYPE_NOT_SET
        if settings.jobspy_is_remote is None:
            remote_text = msg.JOBSPY_SETTINGS_IS_REMOTE_NOT_SET
        else:
            remote_text = "да" if settings.jobspy_is_remote else "нет"

        sites_val = mdv2.code(", ".join(settings.jobspy_sites))
        terms_val = mdv2.code(", ".join(settings.jobspy_search_terms))
        results_val = mdv2.code(str(settings.jobspy_results_wanted))
        hours_val = mdv2.code(str(settings.jobspy_hours_old))

        def _line(label: str, value: str) -> str:
            return f"{mdv2.escape(label)}: {value}"

        lines = [
            mdv2.bold(msg.JOBSPY_SETTINGS_HEADER),
            _line(msg.JOBSPY_SETTINGS_ENABLED, mdv2.code(enabled_text)),
            _line(msg.JOBSPY_SETTINGS_SITES, sites_val),
            _line(msg.JOBSPY_SETTINGS_SEARCH_TERMS, terms_val),
            _line(msg.JOBSPY_SETTINGS_LOCATION, mdv2.code(location_text)),
            _line(msg.JOBSPY_SETTINGS_COUNTRY, mdv2.code(settings.jobspy_country)),
            _line(msg.JOBSPY_SETTINGS_RESULTS, results_val),
            _line(msg.JOBSPY_SETTINGS_HOURS_OLD, hours_val),
            _line(msg.JOBSPY_SETTINGS_JOB_TYPE, mdv2.code(job_type_text)),
            _line(msg.JOBSPY_SETTINGS_IS_REMOTE, mdv2.code(remote_text)),
        ]
        await self._send_message(chat, "\n".join(lines), formatted=True)

    async def handle_jobspy_toggle(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Toggle JobSpy on/off."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        try:
            current = self.settings_manager.get_jobspy_enabled()
            new_value = not current

            from job_finder.db.settings import update_settings_field

            update_settings_field("jobspy_enabled", new_value)
            self.settings_manager.invalidate_cache()
            reply = msg.JOBSPY_TOGGLED_ON if new_value else msg.JOBSPY_TOGGLED_OFF
            await self._send_message(chat, reply)
        except Exception as e:
            logger.exception("Failed to toggle jobspy")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_jobspy_sites(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set active JobSpy sites."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.JOBSPY_SITES_USAGE)
            return

        # Parse comma-separated or space-separated sites
        raw = " ".join(context.args)
        sites = [s.strip().lower() for s in raw.replace(",", " ").split() if s.strip()]
        valid_sites = {"linkedin", "indeed", "glassdoor", "google"}
        invalid = [s for s in sites if s not in valid_sites]
        if invalid:
            await self._send_message(chat, msg.JOBSPY_SITES_INVALID)
            return

        try:
            from job_finder.db.settings import update_settings_field

            update_settings_field("jobspy_sites", sites)
            self.settings_manager.invalidate_cache()
            await self._send_message(chat, msg.JOBSPY_SITES_UPDATED.format(sites=", ".join(sites)))
        except Exception as e:
            logger.exception("Failed to update jobspy_sites")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_jobspy_search(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Set JobSpy search terms."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.JOBSPY_SEARCH_USAGE)
            return

        raw = " ".join(context.args)
        terms = [t.strip() for t in raw.split(",") if t.strip()]
        if not terms:
            await self._send_message(chat, msg.JOBSPY_SEARCH_USAGE)
            return

        try:
            from job_finder.db.settings import update_settings_field

            update_settings_field("jobspy_search_terms", terms)
            self.settings_manager.invalidate_cache()
            await self._send_message(chat, msg.JOBSPY_SEARCH_UPDATED.format(terms=", ".join(terms)))
        except Exception as e:
            logger.exception("Failed to update jobspy_search_terms")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_jobspy_location(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Set JobSpy location."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.JOBSPY_LOCATION_USAGE)
            return

        value = " ".join(context.args).strip()

        try:
            from job_finder.db.settings import update_settings_field

            if value.lower() in ("none", "reset", "clear"):
                update_settings_field("jobspy_location", None)
                self.settings_manager.invalidate_cache()
                await self._send_message(chat, msg.JOBSPY_LOCATION_RESET)
            else:
                update_settings_field("jobspy_location", value)
                self.settings_manager.invalidate_cache()
                await self._send_message(chat, msg.JOBSPY_LOCATION_UPDATED.format(location=value))
        except Exception as e:
            logger.exception("Failed to update jobspy_location")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def handle_jobspy_results(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Set JobSpy results_wanted."""
        chat = await self._ensure_access(update)
        if not chat:
            return
        if not self.settings_manager or not self.settings_manager.is_supabase_available():
            await self._send_message(chat, msg.SETTINGS_DB_UNAVAILABLE)
            return

        if not context.args:
            await self._send_message(chat, msg.JOBSPY_RESULTS_USAGE)
            return

        try:
            count = int(context.args[0])
            if count < 1 or count > 100:
                await self._send_message(chat, msg.JOBSPY_RESULTS_INVALID)
                return

            from job_finder.db.settings import update_settings_field

            update_settings_field("jobspy_results_wanted", count)
            self.settings_manager.invalidate_cache()
            await self._send_message(
                chat,
                msg.JOBSPY_RESULTS_UPDATED.format(count=mdv2.code(str(count))),
                formatted=True,
            )
        except ValueError:
            await self._send_message(chat, msg.JOBSPY_RESULTS_INVALID)
        except Exception as e:
            logger.exception("Failed to update jobspy_results_wanted")
            await self._send_message(chat, msg.SETTINGS_UPDATE_ERROR.format(error=str(e)))

    async def run_polling(self) -> None:
        await self.app.initialize()
        await self.app.start()
        if self.app.updater is None:
            return
        await self.app.updater.start_polling()
        # Keep running until cancelled externally
        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except asyncio.CancelledError:
            pass

    async def shutdown(self) -> None:
        try:
            if self.app.updater is not None:
                await self.app.updater.stop()
            await self.app.stop()
        finally:
            await self.app.shutdown()
