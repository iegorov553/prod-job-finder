from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dotenv import load_dotenv

DEFAULT_CHANNELS: list[str] = []


@dataclass
class Config:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session: str
    telegram_session_base64: str | None
    telegram_string_session: str | None
    telegram_channels: List[str]

    llm_api_key: str
    llm_model_name: str
    llm_base_url: str
    llm_temperature: float | None
    llm_timeout: int
    llm_retry_max: int
    llm_retry_backoff: float

    max_posts_per_batch: int
    max_posts_per_run: int
    hours_lookback: int

    relevant_log_path: Path

    bot_token: str
    allowed_user_ids: List[int]

    # Supabase configuration (required)
    supabase_url: str
    supabase_key: str


def _parse_channels(raw: str | None) -> List[str]:
    if not raw:
        return DEFAULT_CHANNELS.copy()
    channels = [item.strip() for item in raw.split(",") if item.strip()]
    return channels


def _parse_int_list(raw: str | None) -> List[int]:
    if not raw:
        return []
    items: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            items.append(int(part))
        except ValueError:
            continue
    return items


def load_config(env_path: str | None = ".env") -> Config:
    load_dotenv(env_path)
    try:
        telegram_api_id = int(os.environ["TELEGRAM_API_ID"])
    except KeyError as exc:
        raise ValueError("TELEGRAM_API_ID is required") from exc
    telegram_api_hash = os.environ.get("TELEGRAM_API_HASH")
    if not telegram_api_hash:
        raise ValueError("TELEGRAM_API_HASH is required")
    telegram_session = os.environ.get("TELEGRAM_SESSION", "telegram_session")
    telegram_session_base64 = os.environ.get("TELEGRAM_SESSION_BASE64")
    telegram_string_session = os.environ.get("TELEGRAM_STRING_SESSION")
    telegram_channels = _parse_channels(os.environ.get("TELEGRAM_CHANNELS"))

    llm_api_key = os.environ.get("LLM_API_KEY")
    if not llm_api_key:
        raise ValueError("LLM_API_KEY is required")
    llm_model_name = os.environ.get("LLM_MODEL_NAME", "gpt-4.1-mini")
    llm_base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    llm_temperature = os.environ.get("LLM_TEMPERATURE")
    temperature_value = float(llm_temperature) if llm_temperature not in (None, "") else None
    llm_timeout = int(os.environ.get("LLM_TIMEOUT", "60"))
    llm_retry_max = int(os.environ.get("LLM_RETRY_MAX", "2"))
    llm_retry_backoff = float(os.environ.get("LLM_RETRY_BACKOFF", "2.0"))

    max_posts_per_batch = int(os.environ.get("MAX_POSTS_PER_BATCH", "10"))
    max_posts_per_run = int(os.environ.get("MAX_POSTS_PER_RUN", "30"))
    hours_lookback = int(os.environ.get("HOURS_LOOKBACK", "24"))

    relevant_log_path = Path(os.environ.get("RELEVANT_LOG_PATH", "relevant_log.jsonl"))

    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is required for control bot")
    allowed_user_ids = _parse_int_list(
        os.environ.get("ALLOW_USER_IDS") or os.environ.get("TELEGRAM_TARGET_USER_ID")
    )
    if not allowed_user_ids:
        raise ValueError("ALLOW_USER_IDS or TELEGRAM_TARGET_USER_ID is required")

    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url:
        raise ValueError("SUPABASE_URL is required")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY is required")

    return Config(
        telegram_api_id=telegram_api_id,
        telegram_api_hash=telegram_api_hash,
        telegram_session=telegram_session,
        telegram_session_base64=telegram_session_base64,
        telegram_string_session=telegram_string_session,
        telegram_channels=telegram_channels,
        llm_api_key=llm_api_key,
        llm_model_name=llm_model_name,
        llm_base_url=llm_base_url,
        llm_temperature=temperature_value,
        llm_timeout=llm_timeout,
        llm_retry_max=llm_retry_max,
        llm_retry_backoff=llm_retry_backoff,
        max_posts_per_batch=max_posts_per_batch,
        max_posts_per_run=max_posts_per_run,
        hours_lookback=hours_lookback,
        relevant_log_path=relevant_log_path,
        bot_token=bot_token,
        allowed_user_ids=allowed_user_ids,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
    )
