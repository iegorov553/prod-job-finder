from __future__ import annotations

import asyncio
import base64
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, cast

from job_finder import digest, llm_client, scraper
from job_finder.bot_control import BotController, RunResult
from job_finder.config import Config, load_config
from job_finder.db import init_supabase
from job_finder.db.channel_states import (
    ensure_channels_exist,
    get_all_channel_states,
    update_last_message_id,
)
from job_finder.db.models import PostCreate, VacancyCreate
from job_finder.db.posts import create_posts_batch, mark_posts_analyzed
from job_finder.db.settings import ensure_settings_exist
from job_finder.db.vacancies import create_vacancies_batch, get_new_relevant_vacancies
from job_finder.llm_client import LLMConfig
from job_finder.resources import messages
from job_finder.scheduler import PipelineScheduler, SchedulerConfig
from job_finder.settings_manager import SettingsManager, init_settings_manager
from job_finder.utils.locks import PipelineLock

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DIGEST_CACHE_PATH = Path("digest_last.md")
LLM_LOG_DIR = Path("llm_logs")
RELEVANT_LOG_PATH = Path("relevant_log.jsonl")
pipeline_lock = PipelineLock()
scheduler = PipelineScheduler()

# Global settings manager
_settings_manager: SettingsManager | None = None


def _ensure_session_file(
    session_name: str,
    session_base64: str | None,
    string_session: str | None,
    base_dir: Path,
) -> None:
    if string_session:
        return
    session_path = base_dir / f"{session_name}.session"
    if session_path.exists():
        return
    if not session_base64:
        return
    data = base64.b64decode(session_base64)
    session_path.write_bytes(data)
    logger.info("Restored Telethon session file from TELEGRAM_SESSION_BASE64.")


def _build_llm_config(config: Config, settings_manager: SettingsManager) -> LLMConfig:
    """Build LLMConfig from env credentials and database settings."""
    llm_settings = settings_manager.get_llm_config()
    limits = settings_manager.get_processing_limits()

    return LLMConfig(
        api_key=config.llm_api_key,
        base_url=config.llm_base_url,
        model_name=llm_settings["model_name"],
        temperature=llm_settings["temperature"],
        timeout=llm_settings["timeout"],
        retry_max=llm_settings["retry_max"],
        retry_backoff=llm_settings["retry_backoff"],
        max_posts_per_batch=limits["max_posts_per_batch"],
    )


def _safe_json_loads(text: str) -> object | None:
    try:
        return cast(object, json.loads(text))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


async def _run_once(  # noqa: C901
    config: Config,
    settings_manager: SettingsManager,
    channels: list[str],
    limit_posts: int | None = None,
    update_state: bool = True,
    progress_cb: Callable[[int, int], None] | None = None,
) -> str:
    """Run the main pipeline.

    Pipeline steps:
    1. Check for pending posts in DB (for retry_failed)
    2. If no pending posts: Fetch new posts from Telegram
    3. Analyze posts with LLM (multi-vacancy)
    4. Save vacancies to DB
    5. Update channel states in DB (only for new posts)
    6. Build digest from relevant vacancies
    """
    from decimal import Decimal

    from job_finder.db.posts import get_pending_posts

    # Get settings from database
    limits = settings_manager.get_processing_limits()
    hours_lookback = limits["hours_lookback"]
    max_posts_per_run = limits["max_posts_per_run"]
    effective_limit = limit_posts if limit_posts is not None else max_posts_per_run

    # Check for pending posts in DB first (for retry_failed functionality)
    db_posts = get_pending_posts(limit=effective_limit)
    fetched_new = False
    telegram_posts = []  # Store Telegram posts for channel state update

    if db_posts:
        logger.info("Found %s pending posts in DB for analysis", len(db_posts))
    else:
        # No pending posts, fetch new from Telegram
        _ensure_session_file(
            config.telegram_session,
            config.telegram_session_base64,
            config.telegram_string_session,
            Path("."),
        )

        # Ensure channel states exist in DB
        channel_states = ensure_channels_exist(channels)
        channel_state_map = {cs.channel: cs.last_message_id for cs in channel_states}

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
                channel_state_map,
                hours_lookback=hours_lookback,
            )
            posts = posts[:effective_limit]

            if not posts:
                logger.info(messages.NO_NEW_MESSAGES)
                return messages.NO_NEW_MESSAGES

            logger.info("Fetched %s new messages", len(posts))
            telegram_posts = posts  # Save for channel state update

            # Save posts to DB
            posts_to_create = [
                PostCreate(
                    telegram_id=post.id,
                    channel=post.channel,
                    telegram_date=datetime.fromisoformat(post.date.replace("Z", "+00:00"))
                    if post.date
                    else datetime.now(timezone.utc),
                    text_full=post.text,
                    source_link=post.source_link,
                    links=post.links,
                )
                for post in posts
            ]
            db_posts = create_posts_batch(posts_to_create)
            logger.info("Saved %s posts to DB", len(db_posts))
            fetched_new = True

    # Analyze posts with LLM (multi-vacancy)
    llm_logs: list[dict] = []

    # Get custom prompt from settings manager
    custom_prompt = settings_manager.get_custom_prompt()
    if not custom_prompt:
        logger.error("custom_prompt not set in database settings")
        return "Error: custom_prompt not configured. Use /prompt_set to configure."

    # Build LLM config from credentials + settings
    llm_config = _build_llm_config(config, settings_manager)

    analysis_results = llm_client.analyze_posts_db(
        db_posts,
        llm_config,
        custom_prompt,
        logs=llm_logs,
        progress_cb=progress_cb,
    )

    if llm_logs and not any(item.get("parsed_ok") for item in llm_logs if isinstance(item, dict)):
        logger.warning("LLM returned no valid results; state not updated.")
        return "LLM rate limit or parse error. Please try again later."

    # Save vacancies to DB and update post analysis status
    total_vacancies = 0
    relevant_count = 0
    vacancies_counts: dict[int, int] = {}

    for result in analysis_results:
        vacancies_to_create = [
            VacancyCreate(
                post_id=result.post_id,
                title=v.title,
                company=v.company,
                industry=v.industry,
                level=v.level,
                location=v.location,
                remote_type=v.remote_type or "unknown",
                salary_min_usd=Decimal(str(v.salary_min_usd)) if v.salary_min_usd else None,
                salary_max_usd=Decimal(str(v.salary_max_usd)) if v.salary_max_usd else None,
                salary_raw=v.salary_raw,
                language=v.language,
                is_relevant=v.is_relevant,
                relevance_reason=v.relevance_reason,
                raw_snippet=v.raw_snippet,
                apply_link=v.apply_link,
            )
            for v in result.vacancies
        ]
        if vacancies_to_create:
            created = create_vacancies_batch(vacancies_to_create)
            total_vacancies += len(created)
            relevant_count += sum(1 for v in created if v.is_relevant)
            vacancies_counts[result.post_id] = len(created)

    # Mark posts as analyzed
    analyzed_post_ids = [r.post_id for r in analysis_results]
    mark_posts_analyzed(analyzed_post_ids, "completed", vacancies_counts)

    logger.info("Saved %s vacancies (%s relevant)", total_vacancies, relevant_count)

    # Save LLM logs
    if llm_logs:
        LLM_LOG_DIR.mkdir(exist_ok=True)
        log_path = (
            LLM_LOG_DIR / f"llm_log_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        )
        log_path.write_text(json.dumps(llm_logs, ensure_ascii=False, indent=2))

    # Update channel states in DB (only for new posts from Telegram)
    if update_state and fetched_new:
        for channel in channels:
            last_id = scraper.get_max_message_id(telegram_posts, channel)
            if last_id is not None:
                update_last_message_id(channel, last_id)
                logger.info("Updated last_message_id for %s: %s", channel, last_id)

    # Build digest from new relevant vacancies in DB
    relevant_vacancies = get_new_relevant_vacancies(limit=100)

    # Convert VacancyDB to VacancyNormalized for digest
    from job_finder.models import VacancyNormalized

    normalized_for_digest = []
    for v in relevant_vacancies:
        # Get post info for source_channel
        from job_finder.db.posts import get_post_by_id

        post = get_post_by_id(v.post_id)
        source_channel = post.channel if post else ""
        source_link = post.source_link if post else None
        post_date = post.telegram_date if post else None

        normalized_for_digest.append(
            VacancyNormalized(
                id=v.id,
                is_relevant=v.is_relevant,
                relevance_reason=v.relevance_reason or "",
                title=v.title,
                company=v.company,
                industry=v.industry,
                level=v.level,
                role=None,
                location=v.location,
                remote_type=v.remote_type,
                salary_min_usd=float(v.salary_min_usd) if v.salary_min_usd else None,
                salary_max_usd=float(v.salary_max_usd) if v.salary_max_usd else None,
                salary_raw=v.salary_raw,
                language=v.language or "other",
                source_channel=source_channel,
                source_message_id=v.post_id,
                source_link=source_link,
                apply_link=v.apply_link,
                raw_snippet=v.raw_snippet or "",
                post_date=post_date,
            )
        )

    digest_text = digest.build_digest(normalized_for_digest)
    DIGEST_CACHE_PATH.write_text(digest_text)

    return digest_text


def main() -> None:  # noqa: C901
    global _settings_manager

    config = load_config()

    # Initialize Supabase (required)
    init_supabase(config.supabase_url, config.supabase_key)
    logger.info("Supabase initialized successfully")

    # Initialize settings manager and ensure settings exist in DB
    _settings_manager = init_settings_manager()
    ensure_settings_exist()
    logger.info("Settings manager initialized")

    def append_relevant(relevant_text: str, relevant_items: list[dict]) -> None:
        RELEVANT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "count": len(relevant_items),
            "items": relevant_items,
            "digest": relevant_text,
        }
        with RELEVANT_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    async def run_pipeline_and_return(  # noqa: C901
        update_state: bool = True,
        limit_posts: int | None = None,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> RunResult:
        channels = _settings_manager.get_channels() if _settings_manager else []
        log_file: Path | None = None
        async with pipeline_lock.acquire():
            try:
                result_text = await _run_once(
                    config,
                    _settings_manager,
                    channels,
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
                            data = _safe_json_loads(log_file.read_text(encoding="utf-8"))
                            if isinstance(data, list):
                                for batch in data:
                                    if isinstance(batch, dict) and "response_text" in batch:
                                        batch_data = _safe_json_loads(batch["response_text"])
                                        if not isinstance(batch_data, list):
                                            continue
                                        for item in batch_data:
                                            if (
                                                isinstance(item, dict)
                                                and "source_channel" not in item
                                            ):
                                                item["source_channel"] = ""
                                        parsed_relevant.extend(batch_data)
                    if parsed_relevant:
                        append_relevant(result_text, parsed_relevant)
                # pick latest log file if exists
                if LLM_LOG_DIR.exists():
                    log_files = sorted(LLM_LOG_DIR.glob("llm_log_*.json"), reverse=True)
                    if log_files:
                        log_file = log_files[0]
                return RunResult(message=result_text, log_path=str(log_file) if log_file else None)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Pipeline error: %s", exc)
                return RunResult(message=f"Pipeline error: {exc}", log_path=None)

    def status_text() -> str:
        channels = _settings_manager.get_channels() if _settings_manager else []
        channel_states = get_all_channel_states()
        channel_state_map = {cs.channel: cs.last_message_id for cs in channel_states}
        scheduler_cfg = (
            _settings_manager.get_scheduler_config()
            if _settings_manager
            else {"enabled": False, "time_utc": None}
        )

        lines = ["Status:"]
        lines.append(f"Channels: {', '.join(channels) if channels else 'none'}")
        for ch in channels:
            last_id = channel_state_map.get(ch)
            lines.append(f"{ch}: last_message_id={last_id}")
        if scheduler_cfg.get("enabled") and scheduler_cfg.get("time_utc"):
            lines.append(f"Auto-run: daily at {scheduler_cfg['time_utc']} UTC")
        else:
            lines.append("Auto-run: off")
        return "\n".join(lines)

    def last_digest_text() -> str:
        if DIGEST_CACHE_PATH.exists():
            return DIGEST_CACHE_PATH.read_text()
        return ""

    def history_text(limit: int = 10) -> str:
        if not RELEVANT_LOG_PATH.exists():
            return ""
        lines = RELEVANT_LOG_PATH.read_text(encoding="utf-8").splitlines()
        lines = [ln for ln in lines if ln.strip()]
        if not lines:
            return ""
        selected = lines[-limit:]
        parts = []
        for ln in selected:
            rec = _safe_json_loads(ln)
            if not isinstance(rec, dict):
                continue
            ts = rec.get("timestamp", "")
            count = rec.get("count", 0)
            parts.append(f"{ts}: {count} item(s)")
        return "\n".join(parts)

    async def run_pipeline_job() -> None:
        asyncio.create_task(run_pipeline_and_return())

    async def update_schedule(cfg: SchedulerConfig) -> str:
        scheduler.update(cfg, run_pipeline_job)
        return (
            f"Schedule updated: daily at {cfg.time_utc} UTC"
            if cfg.enabled and cfg.time_utc
            else "Auto-run disabled."
        )

    bot = BotController(
        token=config.bot_token,
        allowed_users=config.allowed_user_ids,
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
        history_file=str(RELEVANT_LOG_PATH),
        settings_manager=_settings_manager,
    )

    async def serve() -> None:
        scheduler.start()
        # Load scheduler config from DB
        scheduler_cfg = (
            _settings_manager.get_scheduler_config()
            if _settings_manager
            else {"enabled": False, "time_utc": None}
        )
        initial_scheduler = SchedulerConfig(
            enabled=scheduler_cfg.get("enabled", False),
            time_utc=scheduler_cfg.get("time_utc"),
        )
        scheduler.update(initial_scheduler, run_pipeline_job)
        try:
            await bot.run_polling()
        finally:
            await bot.shutdown()
            scheduler.stop()

    asyncio.run(serve())


if __name__ == "__main__":
    main()
