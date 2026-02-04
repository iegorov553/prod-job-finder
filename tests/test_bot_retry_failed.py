"""Tests for /retry_failed command."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from job_finder.bot_control import BotController, RunResult
from job_finder.resources import messages as msg


@pytest.fixture
def mock_update():
    """Create mock Update object."""
    update = MagicMock()
    update.effective_chat.chat_id = 12345
    update.effective_chat.send_message = AsyncMock()
    update.effective_chat.send_document = AsyncMock()
    update.effective_user.id = 12345
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = MagicMock()
    context.args = []
    return context


@pytest.fixture
def bot_control():
    """Create BotController instance with mocked dependencies."""
    with patch("job_finder.bot_control.ApplicationBuilder"):
        bot = BotController(
            token="test-token",
            allowed_users=[12345],
            on_run=AsyncMock(return_value=RunResult(message="Test result")),
            on_run_preview=AsyncMock(return_value=RunResult(message="Preview")),
            on_schedule_update=AsyncMock(return_value="OK"),
            get_status=lambda: "Status",
            get_digest=lambda: "Digest",
            get_history=lambda: "History",
        )
        bot.settings_manager = MagicMock()
        bot.settings_manager.is_supabase_available.return_value = True
        yield bot


@pytest.mark.asyncio
async def test_retry_failed_no_posts(bot_control, mock_update, mock_context):
    """Should notify user when no failed posts exist."""
    with patch("job_finder.db.posts.get_failed_posts", return_value=[]):
        await bot_control.handle_retry_failed(mock_update, mock_context)

    mock_update.effective_chat.send_message.assert_called_once()
    call_text = mock_update.effective_chat.send_message.call_args[0][0]
    assert "Нет failed постов" in call_text


@pytest.mark.asyncio
async def test_retry_failed_success(bot_control, mock_update, mock_context):
    """Should reset failed posts to pending and trigger analysis."""
    from datetime import datetime, timezone

    from job_finder.db.models import PostDB

    failed_posts = [
        PostDB(
            id=1,
            telegram_id=100,
            channel="@test",
            telegram_date=datetime.now(timezone.utc),
            text_full="Post 1",
            analysis_status="failed",
            vacancies_count=0,
        ),
        PostDB(
            id=2,
            telegram_id=101,
            channel="@test",
            telegram_date=datetime.now(timezone.utc),
            text_full="Post 2",
            analysis_status="failed",
            vacancies_count=0,
        ),
    ]

    mock_mark_analyzed = MagicMock(return_value=2)

    with (
        patch("job_finder.db.posts.get_failed_posts", return_value=failed_posts),
        patch("job_finder.db.posts.mark_posts_analyzed", mock_mark_analyzed),
    ):
        await bot_control.handle_retry_failed(mock_update, mock_context)

    # Should mark posts as pending
    mock_mark_analyzed.assert_called_once()
    call_args = mock_mark_analyzed.call_args
    assert set(call_args[0][0]) == {1, 2}
    assert call_args[1]["status"] == "pending"
    assert call_args[1]["vacancies_counts"] is None

    # Should trigger on_run
    bot_control.on_run.assert_called_once()

    # Should send start message and result
    assert mock_update.effective_chat.send_message.call_count >= 1


@pytest.mark.asyncio
async def test_retry_failed_empty_result_message(bot_control, mock_update, mock_context):
    """Should send fallback message when result text is missing."""
    from datetime import datetime, timezone

    from job_finder.db.models import PostDB

    failed_posts = [
        PostDB(
            id=1,
            telegram_id=100,
            channel="@test",
            telegram_date=datetime.now(timezone.utc),
            text_full="Post 1",
            analysis_status="failed",
            vacancies_count=0,
        ),
    ]

    bot_control.on_run = AsyncMock(return_value=RunResult(message=None))

    with (
        patch("job_finder.db.posts.get_failed_posts", return_value=failed_posts),
        patch("job_finder.db.posts.mark_posts_analyzed", MagicMock(return_value=1)),
    ):
        await bot_control.handle_retry_failed(mock_update, mock_context)

    calls = [call[0][0] for call in mock_update.effective_chat.send_message.call_args_list]
    assert msg.EMPTY_RESULT in calls


@pytest.mark.asyncio
async def test_retry_failed_with_limit(bot_control, mock_update, mock_context):
    """Should respect custom limit argument."""
    from datetime import datetime, timezone

    from job_finder.db.models import PostDB

    failed_posts = [
        PostDB(
            id=1,
            telegram_id=100,
            channel="@test",
            telegram_date=datetime.now(timezone.utc),
            text_full="Post 1",
            analysis_status="failed",
            vacancies_count=0,
        ),
    ]

    mock_context.args = ["10"]
    mock_get_failed = MagicMock(return_value=failed_posts)

    with (
        patch("job_finder.db.posts.get_failed_posts", mock_get_failed),
        patch("job_finder.db.posts.mark_posts_analyzed", MagicMock(return_value=1)),
    ):
        await bot_control.handle_retry_failed(mock_update, mock_context)

    # Should call with custom limit
    mock_get_failed.assert_called_once_with(limit=10)


@pytest.mark.asyncio
async def test_retry_failed_invalid_limit_too_high(bot_control, mock_update, mock_context):
    """Should reject limit > 500."""
    mock_context.args = ["600"]

    await bot_control.handle_retry_failed(mock_update, mock_context)

    mock_update.effective_chat.send_message.assert_called_once()
    call_text = mock_update.effective_chat.send_message.call_args[0][0]
    assert "должен быть от 1 до 500" in call_text


@pytest.mark.asyncio
async def test_retry_failed_invalid_limit_too_low(bot_control, mock_update, mock_context):
    """Should reject limit < 1."""
    mock_context.args = ["0"]

    await bot_control.handle_retry_failed(mock_update, mock_context)

    mock_update.effective_chat.send_message.assert_called_once()
    call_text = mock_update.effective_chat.send_message.call_args[0][0]
    assert "должен быть от 1 до 500" in call_text


@pytest.mark.asyncio
async def test_retry_failed_invalid_limit_not_integer(bot_control, mock_update, mock_context):
    """Should reject non-integer limit."""
    mock_context.args = ["abc"]

    await bot_control.handle_retry_failed(mock_update, mock_context)

    mock_update.effective_chat.send_message.assert_called_once()
    call_text = mock_update.effective_chat.send_message.call_args[0][0]
    assert "должен быть от 1 до 500" in call_text


@pytest.mark.asyncio
async def test_retry_failed_on_run_error(bot_control, mock_update, mock_context):
    """Should handle errors during analysis gracefully."""
    from datetime import datetime, timezone

    from job_finder.db.models import PostDB

    failed_posts = [
        PostDB(
            id=1,
            telegram_id=100,
            channel="@test",
            telegram_date=datetime.now(timezone.utc),
            text_full="Post 1",
            analysis_status="failed",
            vacancies_count=0,
        ),
    ]

    bot_control.on_run = AsyncMock(side_effect=RuntimeError("Analysis failed"))

    with (
        patch("job_finder.db.posts.get_failed_posts", return_value=failed_posts),
        patch("job_finder.db.posts.mark_posts_analyzed", MagicMock(return_value=1)),
    ):
        await bot_control.handle_retry_failed(mock_update, mock_context)

    # Should send error message
    calls = [call[0][0] for call in mock_update.effective_chat.send_message.call_args_list]
    error_sent = any("Ошибка повторного анализа" in call for call in calls)
    assert error_sent


@pytest.mark.asyncio
async def test_retry_failed_no_supabase(bot_control, mock_update, mock_context):
    """Should notify user when Supabase is unavailable."""
    bot_control.settings_manager.is_supabase_available.return_value = False

    await bot_control.handle_retry_failed(mock_update, mock_context)

    mock_update.effective_chat.send_message.assert_called_once()
    call_text = mock_update.effective_chat.send_message.call_args[0][0]
    assert "База данных настроек недоступна" in call_text


@pytest.mark.asyncio
async def test_retry_failed_unauthorized(bot_control, mock_update, mock_context):
    """Should deny access to unauthorized users."""
    mock_update.effective_user.id = 99999  # Not in allowed_users

    await bot_control.handle_retry_failed(mock_update, mock_context)

    # Should send unauthorized message (via _unauthorized_reply)
    mock_update.effective_chat.send_message.assert_called_once_with("Access denied.")
