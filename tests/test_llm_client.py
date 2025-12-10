import json
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from job_finder.config import Config
from job_finder.llm_client import analyze_posts
from job_finder.models import RawPost


class DummyResponse:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Dict[str, Any]:
        return self._payload


def _config(tmp_path) -> Config:
    return Config(
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


def test_analyze_posts_parses_response(monkeypatch, tmp_path) -> None:
    posts = [
        RawPost(
            id=1,
            channel="@a",
            date="2024-01-01T00:00:00Z",
            text="Senior PM remote 120k",
            links=["https://example.com"],
            source_link="https://t.me/a/1",
        )
    ]
    response_content = json.dumps(
        [
            {
                "id": 1,
                "is_relevant": True,
                "relevance_reason": "Senior PM remote",
                "title": "Senior PM",
                "company": "Acme",
                "level": "senior",
                "role": "PM",
                "location": "Remote",
                "remote_type": "remote",
                "salary_min_usd": 110000,
                "salary_max_usd": 130000,
                "salary_raw": "110-130k USD",
                "language": "en",
                "source_channel": "@a",
                "source_message_id": 1,
                "source_link": "https://t.me/a/1",
                "raw_snippet": "snippet",
            }
        ]
    )
    payload = {"choices": [{"message": {"content": response_content}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        assert "Authorization" in headers
        assert "messages" in json
        return DummyResponse(payload)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    result = analyze_posts(posts, _config(tmp_path))
    assert len(result) == 1
    assert result[0].is_relevant is True
    assert result[0].salary_max_usd == 130000


def test_analyze_posts_handles_bad_json(monkeypatch, tmp_path) -> None:
    posts = [
        RawPost(
            id=1,
            channel="@a",
            date="2024-01-01T00:00:00Z",
            text="text",
            links=[],
            source_link="https://t.me/a/1",
        )
    ]
    payload = {"choices": [{"message": {"content": "not json"}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse(payload)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    result = analyze_posts(posts, _config(tmp_path))
    assert result == []
