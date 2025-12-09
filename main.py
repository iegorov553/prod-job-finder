from __future__ import annotations

import asyncio
import logging
import base64
from pathlib import Path

from job_finder import digest, llm_client, scraper, state
from job_finder.config import Config, load_config
from job_finder.resources import messages

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _ensure_session_file(session_name: str, session_base64: str | None, base_dir: Path) -> None:
    session_path = base_dir / f"{session_name}.session"
    if session_path.exists():
        return
    if not session_base64:
        return
    data = base64.b64decode(session_base64)
    session_path.write_bytes(data)
    logger.info("Восстановлен файл сессии Telethon из TELEGRAM_SESSION_BASE64.")


async def _run_once(config: Config) -> None:
    _ensure_session_file(config.telegram_session, config.telegram_session_base64, Path("."))
    current_state = state.load_state(config.state_path, config.telegram_channels)
    client = scraper.create_client(
        config.telegram_api_id,
        config.telegram_api_hash,
        config.telegram_session,
    )
    async with client:
        await client.start()
        posts = await scraper.fetch_new_posts(
            client,
            config.telegram_channels,
            current_state,
            hours_lookback=config.hours_lookback,
        )
        if not posts:
            logger.info(messages.NO_NEW_MESSAGES)
            await client.send_message("me", messages.EMPTY_DIGEST)
            return
        logger.info("Получено %s новых сообщений", len(posts))
        normalized = llm_client.analyze_posts(posts, config)
        relevant = [item for item in normalized if item.is_relevant]
        logger.info("Релевантных вакансий: %s", len(relevant))
        digest_text = digest.build_digest(relevant)
        await client.send_message("me", digest_text, parse_mode="markdown")
        for channel in config.telegram_channels:
            last_id = scraper.get_max_message_id(posts, channel)
            if last_id is not None:
                current_state.update_last_message_id(channel, last_id)
        state.save_state(config.state_path, current_state)


def main() -> None:
    config = load_config()
    asyncio.run(_run_once(config))


if __name__ == "__main__":
    main()
