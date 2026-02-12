from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Callable, Iterable, List, cast
from urllib.parse import urlparse

import requests  # type: ignore[import-untyped]

from job_finder.db.models import (
    LinkType,
    PostAnalysisResult,
    PostDB,
    VacancyFromLLM,
    VacancyLink,
)
from job_finder.db.post_analysis_attempts import create_post_analysis_attempts
from job_finder.db.posts import mark_posts_analyzed
from job_finder.models import Language, RemoteType
from job_finder.resources.messages import ERROR_PARSING_BATCH

logger = logging.getLogger(__name__)

RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
PARSE_FALLBACK_CODES = {"json_parse_error", "empty_response", "post_id_mismatch"}

ALLOWED_LINK_TYPES = {
    "apply_direct",
    "job_board_post",
    "social_post",
    "company_careers",
    "job_description",
    "recruiter_contact",
    "company_website",
    "other",
}


@dataclass
class LLMConfig:
    """Configuration for LLM API calls."""

    api_key: str
    base_url: str
    model_name: str
    temperature: float | None
    timeout: int
    retry_max: int
    retry_backoff: float
    max_posts_per_batch: int


@dataclass
class BatchFailure:
    code: str
    message: str
    http_status: int | None = None
    response_excerpt: str | None = None


def _map_language(value: str | None) -> Language:
    if value in {"en", "ru"}:
        return value  # type: ignore[return-value]
    return "other"


def _map_remote_type(value: str | None) -> RemoteType:
    normalized = (value or "").lower()
    if normalized in {"remote", "hybrid", "onsite"}:
        return normalized  # type: ignore[return-value]
    return "unknown"


def _is_valid_http_url(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_link_type(value: object) -> LinkType:
    if not isinstance(value, str):
        return "other"
    candidate = value.strip().lower()
    if candidate in ALLOWED_LINK_TYPES:
        return cast(LinkType, candidate)
    return cast(LinkType, "other")


def _parse_vacancy_links(raw_links: object) -> list[VacancyLink]:
    if not isinstance(raw_links, list):
        return []
    parsed_links: list[VacancyLink] = []
    for item in raw_links:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not _is_valid_http_url(url):
            continue
        parsed_links.append(
            VacancyLink(
                url=cast(str, url),
                type=_normalize_link_type(item.get("type")),
            )
        )
    return parsed_links


def _build_user_payload_db(posts: List[PostDB]) -> str:
    payload = {
        "posts": [
            {
                "id": post.id,
                "channel": post.channel,
                "text": post.text_full,
                "links": post.links or [],
            }
            for post in posts
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_request_body(custom_prompt: str, user_payload: str, llm_config: LLMConfig) -> dict:
    body: dict = {
        "model": llm_config.model_name,
        "messages": [
            {"role": "system", "content": custom_prompt},
            {"role": "user", "content": user_payload},
        ],
    }
    if llm_config.temperature is not None:
        body["temperature"] = llm_config.temperature
    return body


def _truncate(value: str, limit: int = 2000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def _record_attempt_events(
    posts: List[PostDB],
    run_id: int | None,
    batch_id: str,
    attempt_no: int,
    llm_config: LLMConfig,
    http_status: int | None,
    error_code: str | None,
    error_message: str | None,
    response_excerpt: str | None,
) -> None:
    if run_id is None or not posts:
        return

    rows = [
        {
            "run_id": run_id,
            "post_id": post.id,
            "batch_id": batch_id,
            "attempt_no": attempt_no,
            "model_name": llm_config.model_name,
            "timeout_sec": llm_config.timeout,
            "http_status": http_status,
            "error_code": error_code,
            "error_message": _truncate(error_message or "", 300) if error_message else None,
            "response_excerpt": (
                _truncate(response_excerpt or "", 2000) if response_excerpt else None
            ),
        }
        for post in posts
    ]
    try:
        create_post_analysis_attempts(rows)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to persist post analysis attempts: %s", exc)


def _classify_http_failure(status: int | None) -> str:
    if status is None:
        return "unknown"
    if 400 <= status < 500:
        return "http_4xx"
    if status >= 500:
        return "http_5xx"
    return "unknown"


def _parse_multi_vacancy_response(  # noqa: C901
    response_text: str,
    posts: List[PostDB],
) -> tuple[List[PostAnalysisResult], str | None, str | None]:
    if not response_text:
        logger.warning("%s: empty response", ERROR_PARSING_BATCH)
        return [], "empty_response", "empty response text"

    try:
        parsed = json.loads(response_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s: %s", ERROR_PARSING_BATCH, exc)
        return [], "json_parse_error", str(exc)

    data = parsed
    if isinstance(parsed, dict):
        if "output_text" in parsed and isinstance(parsed["output_text"], str):
            try:
                data = json.loads(parsed["output_text"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s: %s", ERROR_PARSING_BATCH, exc)
                return [], "json_parse_error", str(exc)
        elif "output" in parsed and isinstance(parsed["output"], list):
            texts = [
                item.get("text", "")
                for item in parsed["output"]
                if isinstance(item, dict) and item.get("type") == "output_text"
            ]
            joined = "\n".join(t for t in texts if t)
            try:
                data = json.loads(joined)
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s: %s", ERROR_PARSING_BATCH, exc)
                return [], "json_parse_error", str(exc)

    if not isinstance(data, list):
        logger.warning("%s: response is not a list", ERROR_PARSING_BATCH)
        return [], "json_parse_error", "response is not a list"

    posts_by_id = {post.id: post for post in posts}
    results: List[PostAnalysisResult] = []
    has_mismatch = False

    for item in data:
        if not isinstance(item, dict):
            continue

        raw_post_id = item.get("post_id") or item.get("id")
        if raw_post_id is None:
            logger.warning("Skipping response without post_id: %s", item)
            has_mismatch = True
            continue

        try:
            post_id = int(raw_post_id)
        except (TypeError, ValueError):
            logger.warning("Invalid post_id in response: %s", raw_post_id)
            has_mismatch = True
            continue

        if post_id not in posts_by_id:
            logger.warning("Unknown post_id in response: %s", post_id)
            has_mismatch = True
            continue

        vacancies_raw = item.get("vacancies")
        if vacancies_raw is None:
            vacancies_raw = [item]
        elif not isinstance(vacancies_raw, list):
            vacancies_raw = []

        vacancies: List[VacancyFromLLM] = []
        for v in vacancies_raw:
            if not isinstance(v, dict):
                continue
            try:
                vacancy = VacancyFromLLM(
                    is_relevant=bool(v.get("is_relevant", False)),
                    relevance_reason=v.get("relevance_reason"),
                    title=v.get("title"),
                    company=v.get("company"),
                    industry=v.get("industry"),
                    level=v.get("level"),
                    location=v.get("location"),
                    remote_type=_map_remote_type(v.get("remote_type")),
                    salary_min_usd=v.get("salary_min_usd"),
                    salary_max_usd=v.get("salary_max_usd"),
                    salary_raw=v.get("salary_raw"),
                    language=_map_language(v.get("language")),
                    raw_snippet=v.get("raw_snippet"),
                    apply_link=(
                        v.get("apply_link") if _is_valid_http_url(v.get("apply_link")) else None
                    ),
                    links_json=_parse_vacancy_links(v.get("links_json")),
                )
                vacancies.append(vacancy)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to parse vacancy: %s - %s", v, exc)
                continue

        results.append(PostAnalysisResult(post_id=post_id, vacancies=vacancies))

    if not results:
        if has_mismatch:
            return [], "post_id_mismatch", "no matching post ids in response"
        return [], "json_parse_error", "empty parsed result"

    return results, None, None


def _chunk_posts_db(posts: List[PostDB], size: int) -> Iterable[List[PostDB]]:
    for idx in range(0, len(posts), size):
        yield posts[idx : idx + size]


def _mark_failed_posts(
    failed_posts: List[PostDB],
    failure: BatchFailure,
    attempts_by_post: dict[int, int],
    run_id: int | None,
) -> None:
    if not failed_posts:
        return
    failed_post_ids = [post.id for post in failed_posts]
    mark_posts_analyzed(
        failed_post_ids,
        status="failed",
        vacancies_counts=None,
        analysis_error_code=failure.code,
        analysis_error_message=failure.message,
        analysis_http_status=failure.http_status,
        attempts_by_post=attempts_by_post,
        analysis_run_id=run_id,
    )


def _current_attempt_no(batch: List[PostDB], attempts_by_post: dict[int, int]) -> int:
    if not batch:
        return 1
    return max(attempts_by_post.get(post.id, 0) for post in batch) or 1


def _send_batch_request(
    batch: List[PostDB],
    llm_config: LLMConfig,
    body: dict,
    attempts_by_post: dict[int, int],
    run_id: int | None,
    batch_id: str,
    logs: List[dict] | None,
) -> tuple[requests.Response | None, BatchFailure | None]:
    url = f"{llm_config.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {llm_config.api_key}",
        "Content-Type": "application/json",
    }
    response: requests.Response | None = None
    last_failure: BatchFailure | None = None

    for attempt in range(llm_config.retry_max + 1):
        attempt_no = attempt + 1
        for post in batch:
            attempts_by_post[post.id] = attempts_by_post.get(post.id, 0) + 1

        try:
            response = requests.post(url, headers=headers, json=body, timeout=llm_config.timeout)
            response.raise_for_status()
            _record_attempt_events(
                batch,
                run_id,
                batch_id,
                attempt_no,
                llm_config,
                response.status_code,
                None,
                None,
                response.text,
            )
            return response, None
        except requests.Timeout as exc:
            message = f"LLM timeout after {llm_config.timeout} seconds: {exc}"
            logger.error(message)
            last_failure = BatchFailure(code="timeout", message=message, http_status=None)
            _record_attempt_events(
                batch,
                run_id,
                batch_id,
                attempt_no,
                llm_config,
                None,
                "timeout",
                str(exc),
                None,
            )
        except requests.HTTPError as exc:
            status = response.status_code if response is not None else None
            code = _classify_http_failure(status)
            message = f"LLM request failed: {exc}"
            logger.error(
                "LLM request failed: %s | status=%s | response=%s",
                exc,
                status,
                response.text if response is not None else "",
            )
            last_failure = BatchFailure(
                code=code,
                message=message,
                http_status=status,
                response_excerpt=response.text if response is not None else None,
            )
            _record_attempt_events(
                batch,
                run_id,
                batch_id,
                attempt_no,
                llm_config,
                status,
                code,
                str(exc),
                response.text if response is not None else None,
            )
            if status in RETRYABLE_HTTP_CODES and attempt < llm_config.retry_max:
                backoff = llm_config.retry_backoff * (2**attempt)
                logger.info("Retrying in %.1f sec (attempt %s)", backoff, attempt_no)
                time.sleep(backoff)
                continue
            break
        except requests.RequestException as exc:
            message = f"LLM request failed: {exc}"
            logger.error(message)
            last_failure = BatchFailure(code="unknown", message=message, http_status=None)
            _record_attempt_events(
                batch,
                run_id,
                batch_id,
                attempt_no,
                llm_config,
                None,
                "unknown",
                str(exc),
                None,
            )
            if attempt < llm_config.retry_max:
                backoff = llm_config.retry_backoff * (2**attempt)
                logger.info("Retrying in %.1f sec (attempt %s)", backoff, attempt_no)
                time.sleep(backoff)
                continue
            break

        if attempt < llm_config.retry_max:
            backoff = llm_config.retry_backoff * (2**attempt)
            logger.info("Retrying in %.1f sec (attempt %s)", backoff, attempt_no)
            time.sleep(backoff)

    if logs is not None:
        logs.append(
            {
                "request": body,
                "response_text": response.text if response is not None else "",
                "parsed_ok": False,
            }
        )
    return None, last_failure or BatchFailure(code="unknown", message="Unknown request error")


def _split_and_reanalyze(
    batch: List[PostDB],
    llm_config: LLMConfig,
    custom_prompt: str,
    logs: List[dict] | None,
    attempts_by_post: dict[int, int],
    run_id: int | None,
    batch_id: str,
) -> List[PostAnalysisResult]:
    if len(batch) <= 1:
        return _analyze_batch_with_fallback(
            batch,
            llm_config,
            custom_prompt,
            logs,
            attempts_by_post,
            run_id,
            batch_id,
        )

    next_size = max(1, len(batch) // 2)
    logger.info("Fallback to smaller batches: %s -> %s", len(batch), next_size)
    results: List[PostAnalysisResult] = []
    for index, sub_batch in enumerate(_chunk_posts_db(batch, next_size), start=1):
        sub_batch_id = f"{batch_id}.{index}"
        results.extend(
            _analyze_batch_with_fallback(
                sub_batch,
                llm_config,
                custom_prompt,
                logs,
                attempts_by_post,
                run_id,
                sub_batch_id,
            )
        )
    return results


def _analyze_batch_with_fallback(  # noqa: C901
    batch: List[PostDB],
    llm_config: LLMConfig,
    custom_prompt: str,
    logs: List[dict] | None,
    attempts_by_post: dict[int, int],
    run_id: int | None,
    batch_id: str,
) -> List[PostAnalysisResult]:
    if not batch:
        return []

    user_payload = _build_user_payload_db(batch)
    body = _build_request_body(custom_prompt, user_payload, llm_config)
    logger.info("Sending batch to LLM: %s posts (batch_id=%s)", len(batch), batch_id)

    response, request_failure = _send_batch_request(
        batch,
        llm_config,
        body,
        attempts_by_post,
        run_id,
        batch_id,
        logs,
    )
    if request_failure is not None:
        _mark_failed_posts(batch, request_failure, attempts_by_post, run_id)
        return []

    if response is None:
        _mark_failed_posts(
            batch,
            BatchFailure(code="unknown", message="LLM request failed with empty response object"),
            attempts_by_post,
            run_id,
        )
        return []

    content = response.json()
    message_content = content.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not message_content:
        message_content = response.text

    if not message_content:
        failure = BatchFailure(code="empty_response", message="LLM returned empty response content")
        _record_attempt_events(
            batch,
            run_id,
            batch_id,
            _current_attempt_no(batch, attempts_by_post),
            llm_config,
            response.status_code,
            failure.code,
            failure.message,
            None,
        )
        if logs is not None:
            logs.append({"request": body, "response_text": "", "parsed_ok": False})
        if len(batch) > 1:
            return _split_and_reanalyze(
                batch, llm_config, custom_prompt, logs, attempts_by_post, run_id, batch_id
            )
        _mark_failed_posts(batch, failure, attempts_by_post, run_id)
        return []

    parsed, parse_error_code, parse_error_message = _parse_multi_vacancy_response(
        message_content, batch
    )
    if logs is not None:
        logs.append(
            {
                "request": body,
                "response_text": message_content,
                "parsed_ok": bool(parsed),
            }
        )

    if not parsed:
        failure = BatchFailure(
            code=parse_error_code or "json_parse_error",
            message=parse_error_message or "Failed to parse response",
            http_status=response.status_code,
            response_excerpt=message_content,
        )
        _record_attempt_events(
            batch,
            run_id,
            batch_id,
            _current_attempt_no(batch, attempts_by_post),
            llm_config,
            response.status_code,
            failure.code,
            failure.message,
            message_content,
        )
        if len(batch) > 1 and failure.code in PARSE_FALLBACK_CODES:
            return _split_and_reanalyze(
                batch, llm_config, custom_prompt, logs, attempts_by_post, run_id, batch_id
            )
        _mark_failed_posts(batch, failure, attempts_by_post, run_id)
        return []

    results = list(parsed)
    parsed_ids = {item.post_id for item in parsed}
    missing_posts = [post for post in batch if post.id not in parsed_ids]
    if not missing_posts:
        return results

    recovered = _split_and_reanalyze(
        missing_posts, llm_config, custom_prompt, logs, attempts_by_post, run_id, f"{batch_id}.m"
    )
    results.extend(recovered)
    return results


def analyze_posts_db(  # noqa: C901
    posts: List[PostDB],
    llm_config: LLMConfig,
    custom_prompt: str,
    logs: List[dict] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
    run_id: int | None = None,
    attempts_out: dict[int, int] | None = None,
) -> List[PostAnalysisResult]:
    """Analyze posts from database and return multi-vacancy results."""
    if not custom_prompt:
        raise ValueError("custom_prompt is required. Please set it in database settings.")

    if not posts:
        return []

    all_results: List[PostAnalysisResult] = []
    processed = 0
    total = len(posts)
    attempts_by_post: dict[int, int] = {post.id: 0 for post in posts}

    for batch_index, batch in enumerate(
        _chunk_posts_db(posts, llm_config.max_posts_per_batch),
        start=1,
    ):
        batch_id = f"b{batch_index}"
        batch_results = _analyze_batch_with_fallback(
            batch,
            llm_config,
            custom_prompt,
            logs,
            attempts_by_post,
            run_id,
            batch_id,
        )
        all_results.extend(batch_results)

        processed += len(batch)
        if progress_cb is not None:
            progress_cb(processed, total)

    if attempts_out is not None:
        attempts_out.update(attempts_by_post)

    return all_results
