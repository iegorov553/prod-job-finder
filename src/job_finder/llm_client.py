from __future__ import annotations

import json
import logging
from typing import Iterable, List

import requests

from job_finder.config import Config
from job_finder.models import Language, RawPost, RemoteType, VacancyNormalized
from job_finder.resources.messages import ERROR_PARSING_BATCH
from job_finder.resources.prompts import SYSTEM_PROMPT

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
                raw_snippet=item.get("raw_snippet") or source.text[:500],
            )
        )
    return normalized_list


def analyze_posts(
    posts: List[RawPost],
    config: Config,
    logs: List[dict] | None = None,
) -> List[VacancyNormalized]:
    if not posts:
        return []
    all_results: List[VacancyNormalized] = []
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
        try:
            response = requests.post(url, headers=headers, json=body, timeout=config.llm_timeout)
            response.raise_for_status()
        except requests.Timeout as exc:
            logger.error("LLM timeout after %s seconds: %s", config.llm_timeout, exc)
            continue
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            logger.error(
                "LLM request failed: %s | status=%s | body=%s | response=%s",
                exc,
                response.status_code,
                body,
                response.text,
            )
            continue
        content = response.json()
        message_content = ""
        if use_prompt_id:
            message_content = content.get("output_text", "")
            if not message_content and isinstance(content.get("output"), list):
                texts = [
                    item.get("text", "")
                    for item in content.get("output", [])
                    if isinstance(item, dict) and item.get("type") == "output_text"
                ]
                message_content = "\n".join(t for t in texts if t)
        if not message_content:
            message_content = content.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not message_content:
            message_content = response.text
        if logs is not None:
            logs.append(
                {
                    "request": body,
                    "response_text": message_content,
                }
            )
        if not message_content:
            logger.warning("%s: empty message content", ERROR_PARSING_BATCH)
            continue
        all_results.extend(_parse_batch_response(message_content, batch))
    return all_results
