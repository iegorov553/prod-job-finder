"""Prompt templates for vacancy enrichment LLM tasks."""

from __future__ import annotations

import json

LINK_SELECTOR_SYSTEM_PROMPT = (
    "You help navigate job pages. "
    "Select exactly one best URL that likely leads to the full vacancy description. "
    'Return JSON only: {"selected_url": "https://..."} or {"selected_url": null}.'
)

TEXT_CLEANER_SYSTEM_PROMPT = (
    "You receive raw text extracted from an HTML page. "
    "Return only meaningful vacancy description text, removing navigation, cookies, footer, "
    "login/signup boilerplate, and duplicated UI labels. "
    "If there is no vacancy content, return an empty string."
)


def build_link_selector_user_payload(
    current_url: str,
    candidate_links: list[str],
    vacancy_title: str | None,
    company: str | None,
) -> str:
    payload = {
        "current_url": current_url,
        "vacancy_title": vacancy_title,
        "company": company,
        "candidate_links": candidate_links,
    }
    return json.dumps(payload, ensure_ascii=False)
