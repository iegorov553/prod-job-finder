from __future__ import annotations

import base64
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from job_finder import digest, llm_client, scraper, state
from job_finder.bot_control import BotController, RunResult
from job_finder.config import Config, load_config
from job_finder.resources import messages
from job_finder.scheduler import PipelineScheduler
from job_finder.settings import load_settings, save_settings
from job_finder.utils.locks import PipelineLock

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DIGEST_CACHE_PATH = Path("digest_last.md")
LLM_LOG_DIR = Path("llm_logs")
RELEVANT_LOG_DEFAULT = Path("relevant_log.jsonl")
pipeline_lock = PipelineLock()
scheduler = PipelineScheduler()


def _ensure_session_file(
    session_name: str,
    session_base64: str | None,
    string_session: str | None,
    base_dir: Path,
) -> None:
    if string_session:
        # String session не требует файлового сохранения.
        return
    session_path = base_dir / f"{session_name}.session"
    if session_path.exists():
        return
    if not session_base64:
        return
    data = base64.b64decode(session_base64)
    session_path.write_bytes(data)
    logger.info("Восстановлен файл сессии Telethon из TELEGRAM_SESSION_BASE64.")


async def _run_once(config: Config, channels: list[str]) -> str:
    return await _run_once(config, channels, limit_posts=None, update_state=True)


async def _run_once(
    config: Config,
    channels: list[str],
    limit_posts: int | None = None,
    update_state: bool = True,
    progress_cb: Callable[[int, int], None] | None = None,
) -> str:
    _ensure_session_file(
        config.telegram_session,
        config.telegram_session_base64,
        config.telegram_string_session,
        Path("."),
    )
    current_state = state.load_state(config.state_path, channels)
    client = scraper.create_client(
        config.telegram_api_id,
        config.telegram_api_hash,
        config.telegram_session,
        string_session=config.telegram_string_session,
    )
    async with client:
        await client.start()
        posts = await scraper.fetch_new_posts(
            client,
            channels,
            current_state,
            hours_lookback=config.hours_lookback,
        )
        effective_limit = limit_posts if limit_posts is not None else config.max_posts_per_run
        posts = posts[:effective_limit]
        if not posts:
            logger.info(messages.NO_NEW_MESSAGES)
            return messages.NO_NEW_MESSAGES
        logger.info("Получено %s новых сообщений", len(posts))
        llm_logs: list[dict] = []
        normalized = llm_client.analyze_posts(
            posts,
            config,
            logs=llm_logs,
            progress_cb=progress_cb,
        )
        if llm_logs and not any(item.get("parsed_ok") for item in llm_logs if isinstance(item, dict)):
            logger.warning("LLM не вернул валидные результаты; состояние не обновляем.")
            return "LLM rate limit or parse error. Please try again later."
        relevant = [item for item in normalized if item.is_relevant]
        logger.info("Релевантных вакансий: %s", len(relevant))
        digest_text = digest.build_digest(relevant)
        DIGEST_CACHE_PATH.write_text(digest_text)
        if llm_logs:
            LLM_LOG_DIR.mkdir(exist_ok=True)
            log_path = LLM_LOG_DIR / f"llm_log_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
            log_path.write_text(json.dumps(llm_logs, ensure_ascii=False, indent=2))
        if update_state:
            for channel in channels:
                last_id = scraper.get_max_message_id(posts, channel)
                if last_id is not None:
                    current_state.update_last_message_id(channel, last_id)
            state.save_state(config.state_path, current_state)
        else:
            # even in preview mode keep state as is
            pass
        return digest_text


def main() -> None:
    config = load_config()
    settings_path = getattr(config, "settings_path", Path("settings.json"))

    def load_current_settings():
        return load_settings(settings_path, env_channels=config.telegram_channels)

    settings = load_current_settings()
    save_settings(settings_path, settings)

    relevant_log_path = getattr(config, "relevant_log_path", RELEVANT_LOG_DEFAULT)

    def append_relevant(relevant_text: str, relevant_items: list[dict]) -> None:
        relevant_log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(relevant_items),
            "items": relevant_items,
            "digest": relevant_text,
        }
        with relevant_log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def run_pipeline_and_return(
        update_state: bool = True,
        limit_posts: int | None = None,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> RunResult:
        current_settings = load_current_settings()
        log_file: Path | None = None
        async with pipeline_lock.acquire():
            try:
                result_text = await _run_once(
                    config,
                    current_settings.channels,
                    limit_posts=limit_posts,
                    update_state=update_state,
                    progress_cb=progress_cb,
                )
                if result_text and result_text != messages.NO_NEW_MESSAGES:
                    # Try to append relevant items parsed from last log (if any)
                    parsed_relevant: list[dict] = []
                    if LLM_LOG_DIR.exists():
                        log_files = sorted(LLM_LOG_DIR.glob("llm_log_*.json"), reverse=True)
                        if log_files:
                            log_file = log_files[0]
                            try:
                                data = json.loads(log_file.read_text(encoding="utf-8"))
                                if isinstance(data, list):
                                    # Flatten normalized responses from the last batch
                                    for batch in data:
                                        if isinstance(batch, dict) and "response_text" in batch:
                                            try:
                                                batch_data = json.loads(batch["response_text"])
                                                if isinstance(batch_data, list):
                                                    # enrich with channel id if missing
                                                    for item in batch_data:
                                                        if isinstance(item, dict) and "source_channel" not in item:
                                                            item["source_channel"] = ""
                                                    parsed_relevant.extend(batch_data)
                                            except Exception:
                                                continue
                            except Exception:
                                pass
                    if parsed_relevant:
                        append_relevant(result_text, parsed_relevant)
                # pick latest log file if exists
                if LLM_LOG_DIR.exists():
                    log_files = sorted(LLM_LOG_DIR.glob("llm_log_*.json"), reverse=True)
                    if log_files:
                        log_file = log_files[0]
                return RunResult(message=result_text, log_path=str(log_file) if log_file else None)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Ошибка пайплайна: %s", exc)
                return RunResult(message=f"Ошибка пайплайна: {exc}", log_path=None)

    def status_text() -> str:
        current_settings = load_current_settings()
        st = state.load_state(config.state_path, current_settings.channels)
        lines = ["Статус:"]
        lines.append(
            f"Каналы: {', '.join(current_settings.channels) if current_settings.channels else 'нет'}"
        )
        for ch in current_settings.channels:
            last_id = st.get_last_message_id(ch)
            lines.append(f"{ch}: last_message_id={last_id}")
        if current_settings.scheduler.enabled and current_settings.scheduler.time_utc:
            lines.append(f"Автозапуск: ежедневно в {current_settings.scheduler.time_utc} UTC")
        else:
            lines.append("Автозапуск: выкл")
        return "\n".join(lines)

    def last_digest_text() -> str:
        if DIGEST_CACHE_PATH.exists():
            return DIGEST_CACHE_PATH.read_text()
        return ""

    def history_text(limit: int = 10) -> str:
        if not relevant_log_path.exists():
            return ""
        lines = relevant_log_path.read_text(encoding="utf-8").splitlines()
        lines = [ln for ln in lines if ln.strip()]
        if not lines:
            return ""
        selected = lines[-limit:]
        parts = []
        for ln in selected:
            try:
                rec = json.loads(ln)
                ts = rec.get("timestamp", "")
                count = rec.get("count", 0)
                parts.append(f"{ts}: {count} item(s)")
            except Exception:
                continue
        return "\n".join(parts)

    async def update_schedule(cfg) -> str:
        scheduler.update(cfg, lambda: asyncio.create_task(run_pipeline_and_return()))
        return (
            f"Расписание обновлено: ежедневно в {cfg.time_utc} UTC"
            if cfg.enabled and cfg.time_utc
            else "Автозапуск выключен."
        )

    # Fallbacks for old configs that might not include new fields
    bot_token = getattr(config, "bot_token", None)
    if bot_token is None:
        import os
        bot_token = os.environ.get("BOT_TOKEN")
    allowed_user_ids = getattr(config, "allowed_user_ids", None)
    if allowed_user_ids is None:
        import os

        raw_ids = os.environ.get("ALLOW_USER_IDS") or os.environ.get("TELEGRAM_TARGET_USER_ID")
        allowed_user_ids = []
        if raw_ids:
            for part in raw_ids.split(","):
                part = part.strip()
                if part:
                    try:
                        allowed_user_ids.append(int(part))
                    except ValueError:
                        continue

    bot = BotController(
        token=bot_token,
        allowed_users=allowed_user_ids,
        settings_path=settings_path,
        on_run=lambda progress_cb: run_pipeline_and_return(
            update_state=True, limit_posts=None, progress_cb=progress_cb
        ),
        on_run_preview=lambda progress_cb: run_pipeline_and_return(
            update_state=False, limit_posts=5, progress_cb=progress_cb
        ),
        on_schedule_update=update_schedule,
        get_status=status_text,
        get_digest=last_digest_text,
        get_history=history_text,
        history_file=str(relevant_log_path),
    )

    async def serve() -> None:
        scheduler.start()
        scheduler.update(
            load_current_settings().scheduler,
            lambda: asyncio.create_task(run_pipeline_and_return()),
        )
        try:
            await bot.run_polling()
        finally:
            await bot.shutdown()
            scheduler.stop()

    asyncio.run(serve())


if __name__ == "__main__":
    main()
