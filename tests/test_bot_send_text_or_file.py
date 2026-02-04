"""Tests for sending bot messages with fallback on Markdown errors."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.error import BadRequest

from job_finder.bot_control import BotController


@pytest.fixture
def bot_control():
    """Create BotController instance with mocked dependencies."""
    with patch("job_finder.bot_control.ApplicationBuilder"):
        bot = BotController(
            token="test-token",
            allowed_users=[12345],
            on_run=AsyncMock(),
            on_run_preview=AsyncMock(),
            on_schedule_update=AsyncMock(),
            get_status=lambda: "Status",
            get_digest=lambda: "Digest",
            get_history=lambda: "History",
        )
        yield bot


@pytest.mark.asyncio
async def test_send_text_or_file_fallbacks_to_plain_text_on_markdown_error(bot_control):
    """Should retry sending plain text when Markdown parsing fails."""
    chat = MagicMock()
    chat.send_message = AsyncMock(
        side_effect=[BadRequest("Can't parse entities: error"), None]
    )

    await bot_control._send_text_or_file(
        chat,
        "Broken *markdown",
        "result.txt",
        "Result",
        parse_mode="Markdown",
        disable_link_preview=True,
    )

    assert chat.send_message.call_count == 2
    first_kwargs = chat.send_message.call_args_list[0].kwargs
    second_kwargs = chat.send_message.call_args_list[1].kwargs
    assert first_kwargs["parse_mode"] == "Markdown"
    assert second_kwargs["parse_mode"] is None
