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
    monkeypatch.setenv("STATE_PATH", str(tmp_path / "state.json"))
    config = load_config(env_path=None)
    assert config.telegram_api_id == 123
    assert config.telegram_api_hash == "hash"
    assert config.telegram_channels == ["@a", "@b", "@c"]
    assert config.telegram_session_base64 == "c2Vzc2lvbg=="
    assert config.telegram_string_session == "STRING"
    assert config.state_path == tmp_path / "state.json"


def test_load_config_missing_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    with pytest.raises(ValueError):
        load_config(env_path=None)
