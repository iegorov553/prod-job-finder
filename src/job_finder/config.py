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

    max_posts_per_batch: int
    hours_lookback: int

    state_path: Path


def _parse_channels(raw: str | None) -> List[str]:
    if not raw:
        return DEFAULT_CHANNELS.copy()
    channels = [item.strip() for item in raw.split(",") if item.strip()]
    return channels


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

    max_posts_per_batch = int(os.environ.get("MAX_POSTS_PER_BATCH", "10"))
    hours_lookback = int(os.environ.get("HOURS_LOOKBACK", "24"))

    state_path = Path(os.environ.get("STATE_PATH", "state.json"))

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
        max_posts_per_batch=max_posts_per_batch,
        hours_lookback=hours_lookback,
        state_path=state_path,
    )
