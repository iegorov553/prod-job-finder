from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

URL_PATTERN = re.compile(r"https?://\S+")
TRAILING_PUNCTUATION = ".,;:!?)]}>\"'"


def _normalize_url(url: str) -> str:
    return url.strip().rstrip(TRAILING_PUNCTUATION)


def _collect_text_urls(text: str) -> list[str]:
    return [_normalize_url(match) for match in URL_PATTERN.findall(text)]


def _collect_entity_urls(message: Any) -> list[str]:
    text = getattr(message, "message", "") or ""
    entities = getattr(message, "entities", None) or []
    found: list[str] = []

    for entity in entities:
        entity_url = getattr(entity, "url", None)
        if isinstance(entity_url, str) and entity_url:
            found.append(_normalize_url(entity_url))
            continue

        if hasattr(entity, "offset") and hasattr(entity, "length"):
            offset = getattr(entity, "offset", None)
            length = getattr(entity, "length", None)
            if isinstance(offset, int) and isinstance(length, int):
                raw = text[offset : offset + length]
                if raw.startswith(("http://", "https://")):
                    found.append(_normalize_url(raw))
    return found


def _extract_buttons(reply_markup: Any) -> Iterable[Any]:
    rows = getattr(reply_markup, "rows", None)
    if rows:
        for row in rows:
            for button in getattr(row, "buttons", []) or []:
                yield button
        return

    direct_buttons = getattr(reply_markup, "buttons", None)
    if direct_buttons:
        if direct_buttons and isinstance(direct_buttons[0], list):
            for row in direct_buttons:
                for button in row:
                    yield button
            return
        for button in direct_buttons:
            yield button


def _collect_button_urls(message: Any) -> list[str]:
    reply_markup = getattr(message, "reply_markup", None)
    if reply_markup is None:
        return []
    found: list[str] = []
    for button in _extract_buttons(reply_markup):
        button_url = getattr(button, "url", None)
        if isinstance(button_url, str) and button_url:
            found.append(_normalize_url(button_url))
    return found


def extract_links_from_message(message: Any) -> list[str]:
    text = getattr(message, "message", "") or ""
    urls = _collect_text_urls(text) + _collect_entity_urls(message) + _collect_button_urls(message)

    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped
