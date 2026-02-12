import json
from datetime import datetime, timezone
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import requests

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
        retry_max=0,
        retry_backoff=2.0,
        max_posts_per_batch=10,
    )


def _make_post(post_id: int, text: str, channel: str = "@a") -> PostDB:
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


def test_marks_failed_with_timeout_code(monkeypatch) -> None:
    posts = [_make_post(1, "Test post")]

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        raise requests.Timeout("Request timed out")

    mock_mark_analyzed = MagicMock(return_value=1)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, run_id=42)

    assert result == []
    mock_mark_analyzed.assert_called_once()
    args = mock_mark_analyzed.call_args
    assert args[1]["status"] == "failed"
    assert args[1]["analysis_error_code"] == "timeout"
    assert args[1]["analysis_http_status"] is None
    assert args[1]["analysis_run_id"] == 42


def test_marks_failed_with_http_5xx_code(monkeypatch) -> None:
    posts = [_make_post(1, "Test post")]

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse({}, status_code=503)

    mock_mark_analyzed = MagicMock(return_value=1)

    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, run_id=42)

    assert result == []
    args = mock_mark_analyzed.call_args
    assert args[1]["status"] == "failed"
    assert args[1]["analysis_error_code"] == "http_5xx"
    assert args[1]["analysis_http_status"] == 503


def test_partial_parse_marks_only_missing_posts_failed(monkeypatch) -> None:
    posts = [_make_post(1, "Post 1"), _make_post(2, "Post 2")]
    response_content = json.dumps(
        [
            {
                "post_id": 1,
                "vacancies": [{"is_relevant": True, "title": "PM", "language": "en"}],
            }
        ]
    )
    payload = {"choices": [{"message": {"content": response_content}}]}

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return DummyResponse(payload)

    mock_mark_analyzed = MagicMock(return_value=1)
    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT, run_id=12)

    assert len(result) == 1
    assert result[0].post_id == 1
    mock_mark_analyzed.assert_called_once()
    args = mock_mark_analyzed.call_args
    assert args[0][0] == [2]
    assert args[1]["analysis_error_code"] == "post_id_mismatch"


def test_parse_failure_retries_with_smaller_batches(monkeypatch) -> None:
    posts = [_make_post(1, "Post 1"), _make_post(2, "Post 2")]
    good_payload_1 = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "post_id": 1,
                                "vacancies": [
                                    {"is_relevant": True, "title": "PM1", "language": "en"}
                                ],
                            }
                        ]
                    )
                }
            }
        ]
    }
    good_payload_2 = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        [
                            {
                                "post_id": 2,
                                "vacancies": [
                                    {"is_relevant": False, "title": "PM2", "language": "en"}
                                ],
                            }
                        ]
                    )
                }
            }
        ]
    }
    responses = [
        DummyResponse({"choices": [{"message": {"content": "not-json"}}]}),
        DummyResponse(good_payload_1),
        DummyResponse(good_payload_2),
    ]

    def fake_post(url: str, headers: Dict[str, str], json: Dict[str, Any], timeout: int):
        return responses.pop(0)

    mock_mark_analyzed = MagicMock(return_value=0)
    monkeypatch.setattr("job_finder.llm_client.requests.post", fake_post)
    with patch("job_finder.llm_client.mark_posts_analyzed", mock_mark_analyzed):
        result = analyze_posts_db(posts, _llm_config(), CUSTOM_PROMPT)

    assert len(result) == 2
    assert {item.post_id for item in result} == {1, 2}
    mock_mark_analyzed.assert_not_called()
