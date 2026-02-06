from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration from environment variables.

    Contains only credentials and infrastructure settings.
    Dynamic settings (LLM params, channels, limits) are stored in Supabase.
    """

    # Telegram credentials
    telegram_api_id: int
    telegram_api_hash: str
    telegram_session: str
    telegram_session_base64: str | None
    telegram_string_session: str | None

    # LLM credentials
    llm_api_key: str
    llm_base_url: str

    # Bot credentials
    bot_token: str
    allowed_user_ids: List[int]

    # Supabase credentials
    supabase_url: str
    supabase_key: str

    # API settings
    api_enabled: bool
    api_host: str
    api_port: int
    run_api_token: str | None


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
    """Load configuration from environment variables.

    Only loads credentials and infrastructure settings.
    Dynamic settings are managed via Supabase.
    """
    load_dotenv(env_path)

    # Telegram credentials
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

    # LLM credentials
    llm_api_key = os.environ.get("LLM_API_KEY")
    if not llm_api_key:
        raise ValueError("LLM_API_KEY is required")
    llm_base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")

    # Bot credentials
    bot_token = os.environ.get("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN is required for control bot")
    allowed_user_ids = _parse_int_list(
        os.environ.get("ALLOW_USER_IDS") or os.environ.get("TELEGRAM_TARGET_USER_ID")
    )
    if not allowed_user_ids:
        raise ValueError("ALLOW_USER_IDS or TELEGRAM_TARGET_USER_ID is required")

    # Supabase credentials
    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url:
        raise ValueError("SUPABASE_URL is required")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY is required")

    api_enabled_raw = os.environ.get("API_ENABLED", "false").strip().lower()
    api_enabled = api_enabled_raw in {"1", "true", "yes", "on"}
    api_host = os.environ.get("API_HOST", "0.0.0.0")  # nosec B104
    api_port_raw = os.environ.get("API_PORT") or os.environ.get("PORT") or "8000"
    try:
        api_port = int(api_port_raw)
    except ValueError as exc:
        raise ValueError("API_PORT must be an integer") from exc
    run_api_token = os.environ.get("RUN_API_TOKEN")
    if api_enabled and not run_api_token:
        raise ValueError("RUN_API_TOKEN is required when API_ENABLED is true")

    return Config(
        telegram_api_id=telegram_api_id,
        telegram_api_hash=telegram_api_hash,
        telegram_session=telegram_session,
        telegram_session_base64=telegram_session_base64,
        telegram_string_session=telegram_string_session,
        llm_api_key=llm_api_key,
        llm_base_url=llm_base_url,
        bot_token=bot_token,
        allowed_user_ids=allowed_user_ids,
        supabase_url=supabase_url,
        supabase_key=supabase_key,
        api_enabled=api_enabled,
        api_host=api_host,
        api_port=api_port,
        run_api_token=run_api_token,
    )
