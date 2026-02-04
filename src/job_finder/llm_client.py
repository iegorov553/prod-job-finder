from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Callable, Iterable, List

import requests

from job_finder.db.models import PostAnalysisResult, PostDB, VacancyFromLLM
from job_finder.db.posts import mark_posts_analyzed
from job_finder.models import Language, RemoteType
from job_finder.resources.messages import ERROR_PARSING_BATCH

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuration for LLM API calls.

    Contains credentials from env and settings from database.
    """

    # Credentials (from env)
    api_key: str
    base_url: str

    # Settings (from database)
    model_name: str
    temperature: float | None
    timeout: int
    retry_max: int
    retry_backoff: float
    max_posts_per_batch: int


def _map_language(value: str | None) -> Language:
    if value in {"en", "ru"}:
        return value  # type: ignore[return-value]
    return "other"


def _map_remote_type(value: str | None) -> RemoteType:
    normalized = (value or "").lower()
    if normalized in {"remote", "hybrid", "onsite"}:
        return normalized  # type: ignore[return-value]
    return "unknown"


def _build_user_payload_db(posts: List[PostDB]) -> str:
    """Build user payload from PostDB objects."""
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


def _parse_multi_vacancy_response(  # noqa: C901
    response_text: str,
    posts: List[PostDB],
) -> List[PostAnalysisResult]:
    """Parse LLM response with multiple vacancies per post.

    Expected format:
    [
        {"post_id": 1, "vacancies": [{"is_relevant": true, ...}, ...]},
        {"post_id": 2, "vacancies": []},
        ...
    ]
    """
    if not response_text:
        logger.warning("%s: empty response", ERROR_PARSING_BATCH)
        return []

    try:
        parsed = json.loads(response_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s: %s", ERROR_PARSING_BATCH, exc)
        return []

    data = parsed
    # Handle wrapped response formats
    if isinstance(parsed, dict):
        if "output_text" in parsed and isinstance(parsed["output_text"], str):
            try:
                data = json.loads(parsed["output_text"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("%s: %s", ERROR_PARSING_BATCH, exc)
                return []
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
                return []

    if not isinstance(data, list):
        logger.warning("%s: response is not a list", ERROR_PARSING_BATCH)
        return []

    posts_by_id = {post.id: post for post in posts}
    results: List[PostAnalysisResult] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        # Support both new format (post_id) and legacy format (id)
        raw_post_id = item.get("post_id") or item.get("id")
        if raw_post_id is None:
            logger.warning("Skipping response without post_id: %s", item)
            continue

        try:
            post_id = int(raw_post_id)
        except (TypeError, ValueError):
            logger.warning("Invalid post_id in response: %s", raw_post_id)
            continue

        if post_id not in posts_by_id:
            logger.warning("Unknown post_id in response: %s", post_id)
            continue

        # Support both new format (vacancies array) and legacy format (flat object)
        vacancies_raw = item.get("vacancies")
        if vacancies_raw is None:
            # Legacy format: the item itself is a single vacancy
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
                    apply_link=v.get("apply_link"),
                )
                vacancies.append(vacancy)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to parse vacancy: %s - %s", v, exc)
                continue

        results.append(PostAnalysisResult(post_id=post_id, vacancies=vacancies))

    return results


def _chunk_posts_db(posts: List[PostDB], size: int) -> Iterable[List[PostDB]]:
    """Chunk PostDB list into batches."""
    for idx in range(0, len(posts), size):
        yield posts[idx : idx + size]


def analyze_posts_db(  # noqa: C901
    posts: List[PostDB],
    llm_config: LLMConfig,
    custom_prompt: str,
    logs: List[dict] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> List[PostAnalysisResult]:
    """Analyze posts from database and return multi-vacancy results.

    This function works with PostDB objects and supports extracting
    multiple vacancies from each post using Chat Completions API.

    Args:
        posts: List of PostDB objects to analyze
        llm_config: LLM configuration (credentials + settings)
        custom_prompt: System prompt from database (required)
        logs: Optional list to append debug logs
        progress_cb: Optional callback for progress reporting

    Returns:
        List of PostAnalysisResult with vacancies for each post

    Raises:
        ValueError: If custom_prompt is not provided
    """
    if not custom_prompt:
        raise ValueError("custom_prompt is required. Please set it in database settings.")

    if not posts:
        return []

    all_results: List[PostAnalysisResult] = []
    processed = 0
    total = len(posts)

    for batch in _chunk_posts_db(posts, llm_config.max_posts_per_batch):
        user_payload = _build_user_payload_db(batch)

        # Use Chat Completions API only
        url = f"{llm_config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {llm_config.api_key}",
            "Content-Type": "application/json",
        }

        body: dict = {
            "model": llm_config.model_name,
            "messages": [
                {"role": "system", "content": custom_prompt},
                {"role": "user", "content": user_payload},
            ],
        }
        if llm_config.temperature is not None:
            body["temperature"] = llm_config.temperature

        logger.info("Sending batch to LLM: %s posts", len(batch))
        response = None

        for attempt in range(llm_config.retry_max + 1):
            try:
                response = requests.post(
                    url, headers=headers, json=body, timeout=llm_config.timeout
                )
                response.raise_for_status()
                break
            except requests.Timeout as exc:
                logger.error("LLM timeout after %s seconds: %s", llm_config.timeout, exc)
            except requests.HTTPError as exc:
                status = response.status_code if response is not None else None
                logger.error(
                    "LLM request failed: %s | status=%s | response=%s",
                    exc,
                    status,
                    response.text if response is not None else "",
                )
                if status in {429, 500, 502, 503, 504} and attempt < llm_config.retry_max:
                    backoff = llm_config.retry_backoff * (2**attempt)
                    logger.info("Retrying in %.1f sec (attempt %s)", backoff, attempt + 1)
                    time.sleep(backoff)
                    continue
            break

        if response is None or response.status_code >= 400:
            # Mark posts in failed batch as 'failed'
            failed_post_ids = [post.id for post in batch]
            if failed_post_ids:
                logger.warning("Marking %s posts as failed due to LLM error", len(failed_post_ids))
                mark_posts_analyzed(failed_post_ids, status="failed", vacancies_counts=None)
            processed += len(batch)
            if progress_cb is not None:
                progress_cb(processed, total)
            continue

        content = response.json()
        message_content = content.get("choices", [{}])[0].get("message", {}).get("content", "")

        if not message_content:
            message_content = response.text

        if not message_content:
            logger.warning("%s: empty message content", ERROR_PARSING_BATCH)
            if logs is not None:
                logs.append(
                    {
                        "request": body,
                        "response_text": message_content,
                        "parsed_ok": False,
                    }
                )
            continue

        parsed = _parse_multi_vacancy_response(message_content, batch)

        if logs is not None:
            logs.append(
                {
                    "request": body,
                    "response_text": message_content,
                    "parsed_ok": bool(parsed),
                }
            )

        all_results.extend(parsed)
        processed += len(batch)

        if progress_cb is not None:
            progress_cb(processed, total)

    return all_results
