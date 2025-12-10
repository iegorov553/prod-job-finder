import asyncio
import base64
from types import SimpleNamespace
from typing import List

import pytest

import main as main_module
from job_finder.config import Config
from job_finder.models import RawPost, VacancyNormalized
from job_finder.state import ChannelState, State


class DummyClient:
    def __init__(self):
        self.sent: List[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def start(self):
        return None

    async def send_message(self, target: str, message: str, parse_mode: str | None = None):
        self.sent.append(message)
        return None


@pytest.mark.asyncio
async def test_run_once_sends_digest(monkeypatch, tmp_path):
    config = Config(
        telegram_api_id=1,
        telegram_api_hash="hash",
        telegram_session="session",
        telegram_session_base64=None,
        telegram_string_session=None,
        telegram_channels=["@a"],
        llm_api_key="key",
        llm_model_name="model",
        llm_base_url="https://example.com/v1",
        max_posts_per_batch=10,
        hours_lookback=24,
        state_path=tmp_path / "state.json",
    )
    loaded_state = State(channels=[ChannelState(username="@a", last_message_id=None)])

    dummy_client = DummyClient()

    def fake_create_client(api_id, api_hash, session):
        return dummy_client

    async def fake_fetch_new_posts(client, channels, state_obj, hours_lookback):
        return [
            RawPost(
                id=1,
                channel="@a",
                date="",
                text="Senior PM",
                links=[],
                source_link="https://t.me/a/1",
            )
        ]

    def fake_analyze_posts(posts, config):
        return [
            VacancyNormalized(
                id=1,
                is_relevant=True,
                relevance_reason="ok",
                title="Senior PM",
                company="Acme",
                level="senior",
                role="PM",
                location="Remote",
                remote_type="remote",
                salary_min_usd=None,
                salary_max_usd=None,
                salary_raw=None,
                language="en",
                source_channel="@a",
                source_message_id=1,
                source_link="https://t.me/a/1",
                raw_snippet="Senior PM",
            )
        ]

    saved_state = {}

    def fake_save_state(path, new_state):
        saved_state["last"] = new_state.get_last_message_id("@a")

    monkeypatch.setattr(main_module.scraper, "create_client", fake_create_client)
    monkeypatch.setattr(main_module.scraper, "fetch_new_posts", fake_fetch_new_posts)
    monkeypatch.setattr(main_module.llm_client, "analyze_posts", fake_analyze_posts)
    monkeypatch.setattr(main_module.state, "load_state", lambda path, channels: loaded_state)
    monkeypatch.setattr(main_module.state, "save_state", fake_save_state)

    await main_module._run_once(config)
    assert dummy_client.sent, "Сообщение должно быть отправлено"
    assert saved_state["last"] == 1


def test_ensure_session_file(tmp_path) -> None:
    session_bytes = b"dummy"
    encoded = base64.b64encode(session_bytes).decode()
    session_name = "telegram_session"
    # run helper
    main_module._ensure_session_file(session_name, encoded, tmp_path)
    session_path = tmp_path / f"{session_name}.session"
    assert session_path.exists()
    assert session_path.read_bytes() == session_bytes
