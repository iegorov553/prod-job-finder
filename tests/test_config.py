from pathlib import Path

import pytest

from job_finder.config import load_config


def test_load_config_parses_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("LLM_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("TELEGRAM_SESSION_BASE64", "c2Vzc2lvbg==")
    monkeypatch.setenv("TELEGRAM_STRING_SESSION", "STRING")
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOW_USER_IDS", "1,2")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("API_ENABLED", "true")
    monkeypatch.setenv("API_HOST", "127.0.0.1")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("RUN_API_TOKEN", "secret")

    config = load_config(env_path=None)

    assert config.telegram_api_id == 123
    assert config.telegram_api_hash == "hash"
    assert config.telegram_session_base64 == "c2Vzc2lvbg=="
    assert config.telegram_string_session == "STRING"
    assert config.llm_api_key == "key"
    assert config.llm_base_url == "https://api.example.com/v1"
    assert config.bot_token == "token"
    assert config.allowed_user_ids == [1, 2]
    assert config.supabase_url == "https://test.supabase.co"
    assert config.supabase_key == "test-key"
    assert config.api_enabled is True
    assert config.api_host == "127.0.0.1"
    assert config.api_port == 9000
    assert config.run_api_token == "secret"


def test_load_config_defaults(monkeypatch) -> None:
    """Should use default values when optional vars not provided."""
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOW_USER_IDS", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    config = load_config(env_path=None)

    assert config.telegram_session == "telegram_session"
    assert config.llm_base_url == "https://api.openai.com/v1"
    assert config.api_enabled is False
    assert config.api_host == "0.0.0.0"
    assert config.api_port == 8000
    assert config.run_api_token is None


def test_load_config_missing_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure required vars are absent/invalid
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLOW_USER_IDS", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.setenv("TELEGRAM_API_ID", "", prepend=False)
    monkeypatch.setenv("TELEGRAM_API_HASH", "", prepend=False)
    monkeypatch.setenv("LLM_API_KEY", "", prepend=False)
    monkeypatch.setenv("BOT_TOKEN", "", prepend=False)
    with pytest.raises(ValueError):
        load_config(env_path=None)


def test_load_config_missing_supabase(monkeypatch: pytest.MonkeyPatch) -> None:
    """Supabase is now required - should raise ValueError if missing."""
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOW_USER_IDS", "1")
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    with pytest.raises(ValueError, match="SUPABASE_URL is required"):
        load_config(env_path=None)


def test_load_config_missing_supabase_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Supabase key is required - should raise ValueError if missing."""
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOW_USER_IDS", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    with pytest.raises(ValueError, match="SUPABASE_KEY is required"):
        load_config(env_path=None)


def test_load_config_requires_run_token_when_api_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOW_USER_IDS", "1")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("API_ENABLED", "true")
    monkeypatch.delenv("RUN_API_TOKEN", raising=False)

    with pytest.raises(ValueError, match="RUN_API_TOKEN is required"):
        load_config(env_path=None)
