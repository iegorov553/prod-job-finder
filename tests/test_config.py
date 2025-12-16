import os
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
    monkeypatch.setenv("BOT_TOKEN", "token")
    monkeypatch.setenv("ALLOW_USER_IDS", "1,2")
    monkeypatch.setenv("STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("SETTINGS_PATH", str(tmp_path / "settings.json"))
    monkeypatch.setenv("RELEVANT_LOG_PATH", str(tmp_path / "relevant.jsonl"))
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
    assert config.state_path == tmp_path / "state.json"
    assert config.settings_path == tmp_path / "settings.json"
    assert config.relevant_log_path == tmp_path / "relevant.jsonl"
    assert config.bot_token == "token"
    assert config.allowed_user_ids == [1, 2]


def test_load_config_missing_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure required vars are absent/invalid
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.delenv("ALLOW_USER_IDS", raising=False)
    monkeypatch.setenv("TELEGRAM_API_ID", "", prepend=False)
    monkeypatch.setenv("TELEGRAM_API_HASH", "", prepend=False)
    monkeypatch.setenv("LLM_API_KEY", "", prepend=False)
    monkeypatch.setenv("BOT_TOKEN", "", prepend=False)
    with pytest.raises(ValueError):
        load_config(env_path=None)
