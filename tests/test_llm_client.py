import json
from datetime import datetime, timezone
from typing import Any, Dict, List

import pytest

from job_finder.db.models import PostDB
from job_finder.llm_client import LLMConfig, analyze_posts_db


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


def _llm_config() -> LLMConfig:
    return LLMConfig(
        api_key="test-key",
        base_url="https://example.com/v1",
        model_name="gpt-4.1-mini",
        temperature=None,
        timeout=60,
        retry_max=2,
        retry_backoff=2.0,
        max_posts_per_batch=10,
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


def test_analyze_posts_db_parses_response(monkeypatch) -> None:
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
    result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, logs)
    assert len(result) == 1
    assert result[0].post_id == 1
    assert len(result[0].vacancies) == 1
    assert result[0].vacancies[0].is_relevant is True
    assert result[0].vacancies[0].salary_max_usd == 130000
    assert result[0].vacancies[0].title == "Senior PM"
    assert result[0].vacancies[0].company == "Acme"
    assert logs, "Logs should be collected"


def test_analyze_posts_db_handles_bad_json(monkeypatch) -> None:
    posts = [_make_post(1, "text")]
    payload = {"choices": [{"message": {"content": "not json"}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse(payload)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, [])
    assert result == []


def test_analyze_posts_db_empty_posts() -> None:
    result = analyze_posts_db([], _llm_config(), CUSTOM_PROMPT, [])
    assert result == []


def test_analyze_posts_db_requires_custom_prompt() -> None:
    posts = [_make_post(1, "text")]
    with pytest.raises(ValueError, match="custom_prompt is required"):
        analyze_posts_db(posts, _llm_config(), "", [])

    with pytest.raises(ValueError, match="custom_prompt is required"):
        analyze_posts_db(posts, _llm_config(), None, [])  # type: ignore


def test_analyze_posts_db_multiple_vacancies(monkeypatch) -> None:
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
    result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, [])
    assert len(result) == 1
    assert len(result[0].vacancies) == 2
    assert result[0].vacancies[0].title == "Product Manager"
    assert result[0].vacancies[1].title == "Product Owner"


def test_analyze_posts_db_legacy_format(monkeypatch) -> None:
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
    result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, [])
    assert len(result) == 1
    assert len(result[0].vacancies) == 1
    assert result[0].vacancies[0].title == "Senior Product Manager"


def test_analyze_posts_db_marks_failed_on_http_error(monkeypatch) -> None:
    """Test that posts are marked as failed when LLM returns HTTP error."""
    from unittest.mock import MagicMock, patch

    posts = [_make_post(1, "Test post")]

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse({}, status_code=500)

    mock_mark_analyzed = MagicMock(return_value=1)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, [])

    assert result == []
    mock_mark_analyzed.assert_called_once()
    call_args = mock_mark_analyzed.call_args
    assert call_args[0][0] == [1]  # post_ids
    assert call_args[1]["status"] == "failed"
    assert call_args[1]["vacancies_counts"] is None


def test_analyze_posts_db_marks_failed_on_timeout(monkeypatch) -> None:
    """Test that posts are marked as failed when LLM times out."""
    from unittest.mock import MagicMock, patch

    import requests

    posts = [_make_post(1, "Test post")]

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        raise requests.Timeout("Request timed out")

    mock_mark_analyzed = MagicMock(return_value=1)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, [])

    assert result == []
    mock_mark_analyzed.assert_called_once()
    call_args = mock_mark_analyzed.call_args
    assert call_args[0][0] == [1]  # post_ids
    assert call_args[1]["status"] == "failed"


def test_analyze_posts_db_marks_batch_failed(monkeypatch) -> None:
    """Test that all posts in failed batch are marked as failed."""
    from unittest.mock import MagicMock, patch

    posts = [_make_post(1, "Post 1"), _make_post(2, "Post 2"), _make_post(3, "Post 3")]

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse({}, status_code=429)  # Rate limit

    mock_mark_analyzed = MagicMock(return_value=3)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, [])

    assert result == []
    mock_mark_analyzed.assert_called_once()
    call_args = mock_mark_analyzed.call_args
    assert set(call_args[0][0]) == {1, 2, 3}  # all post_ids
    assert call_args[1]["status"] == "failed"


def test_analyze_posts_db_calls_progress_on_failed_batch(monkeypatch) -> None:
    """Test that progress callback is called even when batch fails."""
    from unittest.mock import MagicMock, patch

    posts = [_make_post(1, "Post 1"), _make_post(2, "Post 2")]

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse({}, status_code=500)

    mock_mark_analyzed = MagicMock(return_value=2)
    mock_progress = MagicMock()

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(
            posts, _llm_config(), CUSTOM_PROMPT, [], progress_cb=mock_progress
        )

    assert result == []
    mock_progress.assert_called_once_with(2, 2)  # processed all posts
