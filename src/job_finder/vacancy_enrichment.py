"""Vacancy text enrichment from external links."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, cast
from urllib.parse import urljoin, urlparse

import requests  # type: ignore[import-untyped]

from job_finder.db.models import VacancyDB, VacancyEnrichmentUpdate
from job_finder.resources.enrichment_prompts import (
    LINK_SELECTOR_SYSTEM_PROMPT,
    TEXT_CLEANER_SYSTEM_PROMPT,
    build_link_selector_user_payload,
)

logger = logging.getLogger(__name__)

HREF_PATTERN = re.compile(r"""href\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)


@dataclass
class EnrichmentConfig:
    api_key: str
    base_url: str
    model_name: str = "gpt-5-nano"
    timeout: int = 30
    max_http_requests_per_vacancy: int = 4
    max_hops: int = 2
    http_timeout: int = 20
    http_retry_max: int = 1


def _is_valid_http_url(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def build_candidate_urls(vacancy: VacancyDB) -> list[str]:
    urls: list[str] = []
    if vacancy.apply_link and _is_valid_http_url(vacancy.apply_link):
        urls.append(vacancy.apply_link)

    for link in vacancy.links_json:
        if _is_valid_http_url(link.url):
            urls.append(link.url)

    unique_urls: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)
    return unique_urls


def _truncate(value: str, limit: int = 15000) -> str:
    if len(value) <= limit:
        return value
    return value[:limit]


def _fetch_html(url: str, http_timeout: int, http_retry_max: int) -> str:
    headers = {"User-Agent": "prod-job-finder/1.0 (+https://github.com)"}
    last_error: Exception | None = None

    for _ in range(http_retry_max + 1):
        try:
            response = requests.get(
                url,
                timeout=http_timeout,
                headers=headers,
                allow_redirects=True,
            )
            response.raise_for_status()
            return cast(str, response.text)
        except requests.RequestException as exc:
            last_error = exc

    raise RuntimeError(f"Failed to fetch URL {url}: {last_error}")


def _extract_main_text(html: str) -> str:
    import trafilatura

    extracted = trafilatura.extract(
        html,
        output_format="txt",
        include_tables=False,
        include_comments=False,
    )
    if not extracted:
        return ""
    return cast(str, extracted).strip()


def _extract_links_from_html(html: str, base_url: str) -> list[str]:
    found = [match.group(1).strip() for match in HREF_PATTERN.finditer(html)]
    urls: list[str] = []
    seen: set[str] = set()
    for href in found:
        absolute = urljoin(base_url, href)
        if not _is_valid_http_url(absolute):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        urls.append(absolute)
    return urls


def _extract_message_content(response_data: dict) -> str:
    choices = response_data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    return ""


def _call_llm(system_prompt: str, user_payload: str, config: EnrichmentConfig) -> str:
    url = f"{config.base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": config.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_payload},
        ],
    }
    response = requests.post(url, headers=headers, json=body, timeout=config.timeout)
    response.raise_for_status()
    response_data = response.json()
    content = _extract_message_content(response_data)
    if content:
        return content
    return cast(str, response.text)


def _select_second_hop_url(
    current_url: str,
    links: list[str],
    vacancy: VacancyDB,
    config: EnrichmentConfig,
) -> str | None:
    if not links:
        return None
    limited_links = links[:25]
    payload = build_link_selector_user_payload(
        current_url=current_url,
        candidate_links=limited_links,
        vacancy_title=vacancy.title,
        company=vacancy.company,
    )
    try:
        response_text = _call_llm(LINK_SELECTOR_SYSTEM_PROMPT, payload, config)
        parsed = json.loads(response_text)
        selected_url = parsed.get("selected_url") if isinstance(parsed, dict) else None
        if _is_valid_http_url(selected_url):
            return str(selected_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to select second hop URL for vacancy %s: %s", vacancy.id, exc)
    return None


def _clean_text_with_llm(raw_text: str, config: EnrichmentConfig) -> str:
    if not raw_text.strip():
        return ""
    payload = _truncate(raw_text, 20000)
    try:
        response_text = _call_llm(TEXT_CLEANER_SYSTEM_PROMPT, payload, config)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to clean extracted text with LLM: %s", exc)
        return ""
    return response_text.strip()


def _success_update(
    vacancy_id: int,
    attempts: int,
    text: str,
    source_url: str,
) -> VacancyEnrichmentUpdate:
    return VacancyEnrichmentUpdate(
        id=vacancy_id,
        enrichment_status="success",
        enrichment_attempts=attempts,
        enrichment_error=None,
        enrichment_completed_at=datetime.now(timezone.utc),
        vacancy_text_full=text,
        vacancy_text_source_url=source_url,
    )


def _failed_update(vacancy_id: int, attempts: int, error: str) -> VacancyEnrichmentUpdate:
    return VacancyEnrichmentUpdate(
        id=vacancy_id,
        enrichment_status="failed",
        enrichment_attempts=attempts,
        enrichment_error=error,
        enrichment_completed_at=datetime.now(timezone.utc),
        vacancy_text_full=None,
        vacancy_text_source_url=None,
    )


def _try_enrich_candidate(
    vacancy: VacancyDB,
    root_url: str,
    config: EnrichmentConfig,
    used_requests: int,
    visited_urls: set[str],
) -> tuple[Optional[VacancyEnrichmentUpdate], int, str | None]:
    current_url = root_url
    hops_used = 0
    attempts = used_requests
    last_error: str | None = None

    while hops_used < config.max_hops and attempts < config.max_http_requests_per_vacancy:
        hops_used += 1
        visited_urls.add(current_url)
        try:
            html = _fetch_html(current_url, config.http_timeout, config.http_retry_max)
        except Exception as exc:  # noqa: BLE001
            attempts += 1
            last_error = str(exc)
            break

        attempts += 1
        raw_text = _extract_main_text(html)
        cleaned_text = _clean_text_with_llm(raw_text, config)
        if cleaned_text:
            return _success_update(vacancy.id, attempts, cleaned_text, current_url), attempts, None

        if hops_used >= config.max_hops:
            last_error = "Vacancy text not found after maximum hops"
            break

        next_links = _extract_links_from_html(html, current_url)
        next_url = _select_second_hop_url(current_url, next_links, vacancy, config)
        if not next_url:
            last_error = "Second hop URL not selected"
            break
        if next_url in visited_urls:
            last_error = "Second hop URL already visited"
            break
        current_url = next_url

    return None, attempts, last_error


def enrich_vacancies(
    vacancies: list[VacancyDB],
    config: EnrichmentConfig,
) -> list[VacancyEnrichmentUpdate]:
    updates: list[VacancyEnrichmentUpdate] = []
    for vacancy in vacancies:
        candidate_urls = build_candidate_urls(vacancy)
        attempts = 0
        visited: set[str] = set()
        last_error = "No candidate URLs for enrichment"
        success: VacancyEnrichmentUpdate | None = None

        for candidate_url in candidate_urls:
            if attempts >= config.max_http_requests_per_vacancy:
                break
            if candidate_url in visited:
                continue
            success, attempts, error = _try_enrich_candidate(
                vacancy,
                candidate_url,
                config,
                attempts,
                visited,
            )
            if success is not None:
                break
            if error:
                last_error = error

        if success is not None:
            updates.append(success)
            continue
        updates.append(_failed_update(vacancy.id, attempts, last_error))

    return updates
