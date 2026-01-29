"""Tests for channel_states CRUD operations.

These tests use mocking to avoid requiring a real Supabase connection.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from job_finder.db.models import ChannelStateCreate, ChannelStateDB


class TestGetChannelState:
    """Tests for get_channel_state function."""

    def test_get_existing_channel_state(self) -> None:
        """Should return ChannelStateDB when channel exists."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "channel": "@test_channel",
                "last_message_id": 12345,
                "updated_at": "2024-01-15T10:00:00Z",
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import get_channel_state

            result = get_channel_state("@test_channel")

        assert result is not None
        assert result.channel == "@test_channel"
        assert result.last_message_id == 12345
        mock_client.table.assert_called_with("channel_states")

    def test_get_non_existing_channel_state(self) -> None:
        """Should return None when channel does not exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import get_channel_state

            result = get_channel_state("@nonexistent")

        assert result is None


class TestGetAllChannelStates:
    """Tests for get_all_channel_states function."""

    def test_get_all_returns_list(self) -> None:
        """Should return list of ChannelStateDB objects."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"channel": "@channel1", "last_message_id": 100, "updated_at": None},
            {"channel": "@channel2", "last_message_id": 200, "updated_at": None},
        ]
        mock_client.table.return_value.select.return_value.execute.return_value = mock_response

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import get_all_channel_states

            result = get_all_channel_states()

        assert len(result) == 2
        assert result[0].channel == "@channel1"
        assert result[1].channel == "@channel2"

    def test_get_all_empty(self) -> None:
        """Should return empty list when no channels exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.select.return_value.execute.return_value = mock_response

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import get_all_channel_states

            result = get_all_channel_states()

        assert result == []


class TestUpsertChannelState:
    """Tests for upsert_channel_state function."""

    def test_upsert_creates_new(self) -> None:
        """Should create new record if channel doesn't exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"channel": "@new_channel", "last_message_id": 999, "updated_at": None}
        ]
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import upsert_channel_state

            data = ChannelStateCreate(channel="@new_channel", last_message_id=999)
            result = upsert_channel_state(data)

        assert result.channel == "@new_channel"
        assert result.last_message_id == 999
        mock_client.table.return_value.upsert.assert_called_once()

    def test_upsert_updates_existing(self) -> None:
        """Should update existing record if channel exists."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"channel": "@existing", "last_message_id": 500, "updated_at": None}
        ]
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import upsert_channel_state

            data = ChannelStateCreate(channel="@existing", last_message_id=500)
            result = upsert_channel_state(data)

        assert result.last_message_id == 500


class TestUpdateLastMessageId:
    """Tests for update_last_message_id convenience function."""

    def test_update_last_message_id(self) -> None:
        """Should update last_message_id for a channel."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"channel": "@channel", "last_message_id": 777, "updated_at": None}
        ]
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import update_last_message_id

            result = update_last_message_id("@channel", 777)

        assert result.last_message_id == 777


class TestDeleteChannelState:
    """Tests for delete_channel_state function."""

    def test_delete_existing(self) -> None:
        """Should delete channel state and return True."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"channel": "@deleted"}]
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import delete_channel_state

            result = delete_channel_state("@deleted")

        assert result is True

    def test_delete_non_existing(self) -> None:
        """Should return False when channel doesn't exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.channel_states.get_supabase_client", return_value=mock_client):
            from job_finder.db.channel_states import delete_channel_state

            result = delete_channel_state("@nonexistent")

        assert result is False
