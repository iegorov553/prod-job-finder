from pathlib import Path

import pytest

from job_finder.config import load_config


def test_load_config_parses_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TELEGRAM_API_ID", "123")
    monkeypatch.setenv("TELEGRAM_API_HASH", "hash")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("TELEGRAM_CHANNELS", "@a,@b , @c")
    monkeypatch.setenv("TELEGRAM_SESSION_BASE64", "c2Vzc2lvbg==")
    monkeypatch.setenv("TELEGRAM_STRING_SESSION", "STRING")
    monkeypatch.setenv("LLM_TIMEOUT", "90")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_PROMPT_ID", "pmpt_123")
    monkeypatch.setenv("LLM_PROMPT_VERSION", "2")
    monkeypatch.setenv("LLM_RETRY_MAX", "3")
    monkeypatch.setenv("LLM_RETRY_BACKOFF", "1.5")
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOW_USER_IDS", "1,2")
    monkeypatch.setenv("MAX_POSTS_PER_RUN", "30")
    monkeypatch.setenv("RELEVANT_LOG_PATH", str(tmp_path / "relevant.jsonl"))
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    config = load_config(env_path=None)
    assert config.telegram_api_id == 123
    assert config.telegram_api_hash == "hash"
    assert config.telegram_channels == ["@a", "@b", "@c"]
    assert config.telegram_session_base64 == "c2Vzc2lvbg=="
    assert config.telegram_string_session == "STRING"
    assert config.llm_temperature == 0.2
    assert config.llm_timeout == 90
    assert config.llm_prompt_id == "pmpt_123"
    assert config.llm_prompt_version == "2"
    assert config.llm_retry_max == 3
    assert config.llm_retry_backoff == 1.5
    assert config.max_posts_per_run == 30
    assert config.relevant_log_path == tmp_path / "relevant.jsonl"
    assert config.bot_token == "token"
    assert config.allowed_user_ids == [1, 2]
    assert config.supabase_url == "https://test.supabase.co"
    assert config.supabase_key == "test-key"


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
