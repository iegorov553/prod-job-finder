import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from job_finder.config import Config
from job_finder.db.models import PostDB
from job_finder.llm_client import analyze_posts_db


class DummyResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            from requests import HTTPError

            raise HTTPError(f"HTTP {self.status_code}")

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
        llm_temperature=None,
        llm_timeout=60,
        llm_retry_max=2,
        llm_retry_backoff=2.0,
        max_posts_per_batch=10,
        max_posts_per_run=30,
        hours_lookback=24,
        relevant_log_path=tmp_path / "rel.jsonl",
        bot_token="token",
        allowed_user_ids=[1],
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )


def _make_post(post_id: int, text: str, channel: str = "@a") -> PostDB:
    """Create a PostDB object for testing."""
    return PostDB(
        id=post_id,
        telegram_id=post_id,
        channel=channel,
        telegram_date=datetime.now(timezone.utc),
        text_full=text,
        source_link=f"https://t.me/{channel.lstrip('@')}/{post_id}",
        links=[],
        analysis_status="pending",
        vacancies_count=0,
    )


CUSTOM_PROMPT = "You are an assistant that evaluates job posts."


def test_analyze_posts_db_parses_response(monkeypatch, tmp_path) -> None:
    posts = [_make_post(1, "Senior PM remote 120k")]
    response_content = json.dumps(
        [
            {
                "post_id": 1,
                "vacancies": [
                    {
                        "is_relevant": True,
                        "relevance_reason": "Senior PM remote",
                        "title": "Senior PM",
                        "company": "Acme",
                        "industry": "Tech",
                        "level": "senior",
                        "location": "Remote",
                        "remote_type": "remote",
                        "salary_min_usd": 110000,
                        "salary_max_usd": 130000,
                        "salary_raw": "110-130k USD",
                        "language": "en",
                        "raw_snippet": "snippet",
                        "apply_link": "https://example.com/apply",
                    }
                ],
            }
        ]
    )
    payload = {"choices": [{"message": {"content": response_content}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        assert "Authorization" in headers
        assert "messages" in json
        return DummyResponse(payload)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    logs: List[dict] = []
    result = analyze_posts_db(posts, _config(tmp_path), logs, custom_prompt=CUSTOM_PROMPT)
    assert len(result) == 1
    assert result[0].post_id == 1
    assert len(result[0].vacancies) == 1
    assert result[0].vacancies[0].is_relevant is True
    assert result[0].vacancies[0].salary_max_usd == 130000
    assert result[0].vacancies[0].title == "Senior PM"
    assert result[0].vacancies[0].company == "Acme"
    assert logs, "Logs should be collected"


def test_analyze_posts_db_handles_bad_json(monkeypatch, tmp_path) -> None:
    posts = [_make_post(1, "text")]
    payload = {"choices": [{"message": {"content": "not json"}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse(payload)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    result = analyze_posts_db(posts, _config(tmp_path), [], custom_prompt=CUSTOM_PROMPT)
    assert result == []


def test_analyze_posts_db_empty_posts(tmp_path) -> None:
    result = analyze_posts_db([], _config(tmp_path), [], custom_prompt=CUSTOM_PROMPT)
    assert result == []


def test_analyze_posts_db_requires_custom_prompt(tmp_path) -> None:
    posts = [_make_post(1, "text")]
    with pytest.raises(ValueError, match="custom_prompt is required"):
        analyze_posts_db(posts, _config(tmp_path), [], custom_prompt=None)

    with pytest.raises(ValueError, match="custom_prompt is required"):
        analyze_posts_db(posts, _config(tmp_path), [], custom_prompt="")


def test_analyze_posts_db_multiple_vacancies(monkeypatch, tmp_path) -> None:
    posts = [_make_post(1, "Multiple positions: PM and PO")]
    response_content = json.dumps(
        [
            {
                "post_id": 1,
                "vacancies": [
                    {
                        "is_relevant": True,
                        "relevance_reason": "Product Manager",
                        "title": "Product Manager",
                        "company": "Acme",
                        "level": "senior",
                        "remote_type": "remote",
                        "language": "en",
                    },
                    {
                        "is_relevant": True,
                        "relevance_reason": "Product Owner",
                        "title": "Product Owner",
                        "company": "Acme",
                        "level": "middle",
                        "remote_type": "hybrid",
                        "language": "en",
                    },
                ],
            }
        ]
    )
    payload = {"choices": [{"message": {"content": response_content}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse(payload)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    result = analyze_posts_db(posts, _config(tmp_path), [], custom_prompt=CUSTOM_PROMPT)
    assert len(result) == 1
    assert len(result[0].vacancies) == 2
    assert result[0].vacancies[0].title == "Product Manager"
    assert result[0].vacancies[1].title == "Product Owner"


def test_analyze_posts_db_legacy_format(monkeypatch, tmp_path) -> None:
    """Test backward compatibility with legacy response format (flat object)."""
    posts = [_make_post(1, "Senior PM position")]
    response_content = json.dumps(
        [
            {
                "id": 1,
                "is_relevant": True,
                "relevance_reason": "Senior PM",
                "title": "Senior Product Manager",
                "company": "TechCo",
                "level": "senior",
                "remote_type": "remote",
                "language": "en",
            }
        ]
    )
    payload = {"choices": [{"message": {"content": response_content}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse(payload)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    result = analyze_posts_db(posts, _config(tmp_path), [], custom_prompt=CUSTOM_PROMPT)
    assert len(result) == 1
    assert len(result[0].vacancies) == 1
    assert result[0].vacancies[0].title == "Senior Product Manager"
