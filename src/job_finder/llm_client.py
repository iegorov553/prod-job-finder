from __future__ import annotations

import json
import logging
import time
from typing import Callable, Iterable, List

import requests

from job_finder.config import Config
from job_finder.db.models import PostAnalysisResult, PostDB, VacancyFromLLM
from job_finder.models import Language, RawPost, RemoteType, VacancyNormalized
from job_finder.resources.messages import ERROR_PARSING_BATCH
from job_finder.resources.prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_MULTI_VACANCY

logger = logging.getLogger(__name__)


def _system_prompt() -> str:
    return SYSTEM_PROMPT


def _chunk_posts(posts: List[RawPost], size: int) -> Iterable[List[RawPost]]:
    for idx in range(0, len(posts), size):
        yield posts[idx : idx + size]


def _build_user_payload(posts: List[RawPost]) -> str:
    payload = {
        "posts": [
            {
                "id": post.id,
                "channel": post.channel,
                "text": post.text,
                "links": post.links,
            }
            for post in posts
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


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


def _parse_multi_vacancy_response(
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


def _extract_output_text_from_response(content: dict) -> str:
    # Try common fields from Responses API
    if "output_text" in content and isinstance(content["output_text"], str):
        return content["output_text"]
    # Try nested output -> message -> content -> output_text
    outputs = content.get("output")
    texts: list[str] = []
    if isinstance(outputs, list):
        for item in outputs:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            for piece in item.get("content", []):
                if isinstance(piece, dict) and piece.get("type") == "output_text":
                    text_val = piece.get("text", "")
                    if text_val:
                        texts.append(text_val)
    return "\n".join(t for t in texts if t)


def _parse_batch_response(
    response_text: str,
    posts: List[RawPost],
) -> List[VacancyNormalized]:
    if not response_text:
        logger.warning("%s: empty response", ERROR_PARSING_BATCH)
        return []
    try:
        parsed = json.loads(response_text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("%s: %s", ERROR_PARSING_BATCH, exc)
        return []

    data = parsed
    # If the parsed object is a dict (e.g., full response), try extracting output_text or output array
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
    normalized_list: List[VacancyNormalized] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if raw_id is None:
            logger.warning("Пропуск ответа без id: %s", item)
            continue
        try:
            post_id = int(raw_id)
        except (TypeError, ValueError):
            logger.warning("Некорректный id в ответе: %s", raw_id)
            continue
        source = posts_by_id.get(post_id)
        if not source:
            continue
        normalized_list.append(
            VacancyNormalized(
                id=post_id,
                is_relevant=bool(item.get("is_relevant")),
                relevance_reason=str(item.get("relevance_reason", "")),
                title=item.get("title"),
                company=item.get("company"),
                industry=item.get("industry"),
                level=item.get("level"),
                role=item.get("role"),
                location=item.get("location"),
                remote_type=_map_remote_type(item.get("remote_type")),
                salary_min_usd=item.get("salary_min_usd"),
                salary_max_usd=item.get("salary_max_usd"),
                salary_raw=item.get("salary_raw"),
                language=_map_language(item.get("language")),
                source_channel=item.get("source_channel") or source.channel,
                source_message_id=item.get("source_message_id") or source.id,
                source_link=item.get("source_link") or source.source_link,
                apply_link=item.get("apply_link"),
                raw_snippet=item.get("raw_snippet") or source.text[:500],
            )
        )
    return normalized_list


def analyze_posts(
    posts: List[RawPost],
    config: Config,
    logs: List[dict] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> List[VacancyNormalized]:
    if not posts:
        return []
    all_results: List[VacancyNormalized] = []
    processed = 0
    total = len(posts)
    for batch in _chunk_posts(posts, config.max_posts_per_batch):
        user_payload = _build_user_payload(batch)
        # If prompt_id provided, use Responses API; otherwise Chat Completions
        use_prompt_id = bool(config.llm_prompt_id)
        url = (
            f"{config.llm_base_url.rstrip('/')}/responses"
            if use_prompt_id
            else f"{config.llm_base_url.rstrip('/')}/chat/completions"
        )
        headers = {
            "Authorization": f"Bearer {config.llm_api_key}",
            "Content-Type": "application/json",
        }
        if use_prompt_id:
            body = {
                "model": config.llm_model_name,
                "prompt": {
                    "id": config.llm_prompt_id,
                    "version": config.llm_prompt_version,
                },
                "input": [{"role": "user", "content": user_payload}],
            }
            if config.llm_temperature is not None:
                body["temperature"] = config.llm_temperature
        else:
            body = {
                "model": config.llm_model_name,
                "messages": [
                    {"role": "system", "content": _system_prompt()},
                    {"role": "user", "content": user_payload},
                ],
            }
            if config.llm_temperature is not None:
                body["temperature"] = config.llm_temperature
        logger.info("Отправка батча в LLM: %s постов", len(batch))
        response = None
        retry_max = getattr(config, "llm_retry_max", 0)
        retry_backoff = getattr(config, "llm_retry_backoff", 2.0)
        for attempt in range(retry_max + 1):
            try:
                response = requests.post(url, headers=headers, json=body, timeout=config.llm_timeout)
                response.raise_for_status()
                break
            except requests.Timeout as exc:
                logger.error("LLM timeout after %s seconds: %s", config.llm_timeout, exc)
            except requests.HTTPError as exc:
                status = response.status_code if response is not None else None
                logger.error(
                    "LLM request failed: %s | status=%s | body=%s | response=%s",
                    exc,
                    status,
                    body,
                    response.text if response is not None else "",
                )
                if status in {429, 500, 502, 503, 504} and attempt < retry_max:
                    backoff = retry_backoff * (2**attempt)
                    logger.info("Повтор через %.1f сек (attempt %s)", backoff, attempt + 1)
                    time.sleep(backoff)
                    continue
            break
        if response is None or response.status_code >= 400:
            continue
        content = response.json()
        message_content = ""
        if use_prompt_id:
            message_content = _extract_output_text_from_response(content)
        if not message_content:
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
        parsed = _parse_batch_response(message_content, batch)
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


def _chunk_posts_db(posts: List[PostDB], size: int) -> Iterable[List[PostDB]]:
    """Chunk PostDB list into batches."""
    for idx in range(0, len(posts), size):
        yield posts[idx : idx + size]


def analyze_posts_db(
    posts: List[PostDB],
    config: Config,
    logs: List[dict] | None = None,
    progress_cb: Callable[[int, int], None] | None = None,
) -> List[PostAnalysisResult]:
    """Analyze posts from database and return multi-vacancy results.

    This is the new analysis function that works with PostDB objects
    and supports extracting multiple vacancies from each post.

    Args:
        posts: List of PostDB objects to analyze
        config: Application configuration
        logs: Optional list to append debug logs
        progress_cb: Optional callback for progress reporting

    Returns:
        List of PostAnalysisResult with vacancies for each post
    """
    if not posts:
        return []

    all_results: List[PostAnalysisResult] = []
    processed = 0
    total = len(posts)

    for batch in _chunk_posts_db(posts, config.max_posts_per_batch):
        user_payload = _build_user_payload_db(batch)

        # If prompt_id provided, use Responses API; otherwise Chat Completions
        use_prompt_id = bool(config.llm_prompt_id)
        url = (
            f"{config.llm_base_url.rstrip('/')}/responses"
            if use_prompt_id
            else f"{config.llm_base_url.rstrip('/')}/chat/completions"
        )
        headers = {
            "Authorization": f"Bearer {config.llm_api_key}",
            "Content-Type": "application/json",
        }

        if use_prompt_id:
            body = {
                "model": config.llm_model_name,
                "prompt": {
                    "id": config.llm_prompt_id,
                    "version": config.llm_prompt_version,
                },
                "input": [{"role": "user", "content": user_payload}],
            }
            if config.llm_temperature is not None:
                body["temperature"] = config.llm_temperature
        else:
            body = {
                "model": config.llm_model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_MULTI_VACANCY},
                    {"role": "user", "content": user_payload},
                ],
            }
            if config.llm_temperature is not None:
                body["temperature"] = config.llm_temperature

        logger.info("Sending batch to LLM: %s posts", len(batch))
        response = None
        retry_max = getattr(config, "llm_retry_max", 0)
        retry_backoff = getattr(config, "llm_retry_backoff", 2.0)

        for attempt in range(retry_max + 1):
            try:
                response = requests.post(url, headers=headers, json=body, timeout=config.llm_timeout)
                response.raise_for_status()
                break
            except requests.Timeout as exc:
                logger.error("LLM timeout after %s seconds: %s", config.llm_timeout, exc)
            except requests.HTTPError as exc:
                status = response.status_code if response is not None else None
                logger.error(
                    "LLM request failed: %s | status=%s | response=%s",
                    exc,
                    status,
                    response.text if response is not None else "",
                )
                if status in {429, 500, 502, 503, 504} and attempt < retry_max:
                    backoff = retry_backoff * (2**attempt)
                    logger.info("Retrying in %.1f sec (attempt %s)", backoff, attempt + 1)
                    time.sleep(backoff)
                    continue
            break

        if response is None or response.status_code >= 400:
            continue

        content = response.json()
        message_content = ""

        if use_prompt_id:
            message_content = _extract_output_text_from_response(content)

        if not message_content:
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
