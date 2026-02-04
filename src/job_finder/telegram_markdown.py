"""Helpers for safe Telegram MarkdownV2 formatting."""

from __future__ import annotations

import re

_MDV2_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"
_MDV2_ESCAPE_RE = re.compile(rf"([{re.escape(_MDV2_SPECIAL_CHARS)}])")


def escape(text: str) -> str:
    """Escape MarkdownV2 special characters in plain text."""
    return _MDV2_ESCAPE_RE.sub(r"\\\1", text)


def escape_code(text: str) -> str:
    """Escape text for inline code in MarkdownV2."""
    return text.replace("\\", "\\\\").replace("`", "\\`")


def escape_pre(text: str) -> str:
    """Escape text for pre blocks in MarkdownV2."""
    return text.replace("\\", "\\\\").replace("`", "\\`")


def escape_url(url: str) -> str:
    """Escape URL for MarkdownV2 link targets."""
    return url.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def bold(text: str) -> str:
    return f"*{escape(text)}*"


def italic(text: str) -> str:
    return f"_{escape(text)}_"


def code(text: str) -> str:
    return f"`{escape_code(text)}`"


def pre(text: str) -> str:
    return f"```\n{escape_pre(text)}\n```"


def link(text: str, url: str, *, escape_text: bool = True) -> str:
    safe_text = escape(text) if escape_text else text
    return f"[{safe_text}]({escape_url(url)})"
