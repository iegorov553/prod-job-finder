from __future__ import annotations

import base64
import asyncio
import logging
from pathlib import Path

from job_finder import digest, llm_client, scraper, state
from job_finder.bot_control import BotController
from job_finder.config import Config, load_config
from job_finder.resources import messages
from job_finder.scheduler import PipelineScheduler
from job_finder.settings import load_settings, save_settings
from job_finder.utils.locks import PipelineLock

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DIGEST_CACHE_PATH = Path("digest_last.md")
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
        if not posts:
            logger.info(messages.NO_NEW_MESSAGES)
            return messages.NO_NEW_MESSAGES
        logger.info("Получено %s новых сообщений", len(posts))
        normalized = llm_client.analyze_posts(posts, config)
        relevant = [item for item in normalized if item.is_relevant]
        logger.info("Релевантных вакансий: %s", len(relevant))
        digest_text = digest.build_digest(relevant)
        DIGEST_CACHE_PATH.write_text(digest_text)
        for channel in channels:
            last_id = scraper.get_max_message_id(posts, channel)
            if last_id is not None:
                current_state.update_last_message_id(channel, last_id)
        state.save_state(config.state_path, current_state)
        return digest_text


def main() -> None:
    config = load_config()
    settings_path = getattr(config, "settings_path", Path("settings.json"))
    settings = load_settings(settings_path, env_channels=config.telegram_channels)
    save_settings(settings_path, settings)

    async def run_pipeline_and_return() -> str:
        async with pipeline_lock.acquire():
            try:
                return await _run_once(config, settings.channels)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Ошибка пайплайна: %s", exc)
                return f"Ошибка пайплайна: {exc}"

    def status_text() -> str:
        st = state.load_state(config.state_path, settings.channels)
        lines = ["Статус:"]
        lines.append(f"Каналы: {', '.join(settings.channels) if settings.channels else 'нет'}")
        for ch in settings.channels:
            last_id = st.get_last_message_id(ch)
            lines.append(f"{ch}: last_message_id={last_id}")
        if settings.scheduler.enabled and settings.scheduler.time_utc:
            lines.append(f"Автозапуск: ежедневно в {settings.scheduler.time_utc} UTC")
        else:
            lines.append("Автозапуск: выкл")
        return "\n".join(lines)

    def last_digest_text() -> str:
        if DIGEST_CACHE_PATH.exists():
            return DIGEST_CACHE_PATH.read_text()
        return ""

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
        on_run=run_pipeline_and_return,
        on_schedule_update=update_schedule,
        get_status=status_text,
        get_digest=last_digest_text,
    )

    scheduler.start()
    scheduler.update(settings.scheduler, lambda: asyncio.create_task(run_pipeline_and_return()))

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bot.run_polling())
    finally:
        loop.run_until_complete(bot.shutdown())
        scheduler.stop()


if __name__ == "__main__":
    main()
