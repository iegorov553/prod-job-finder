"""Tests for settings CRUD operations."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from job_finder.db.models import SettingsDB, SettingsUpdate


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_success(self) -> None:
        """Should return SettingsDB when settings exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "channels": ["@channel1", "@channel2"],
                "scheduler_enabled": True,
                "scheduler_time_utc": "09:00",
                "llm_model_name": "gpt-4o",
                "llm_temperature": "0.7",
                "llm_timeout": 120,
                "llm_retry_max": 3,
                "llm_retry_backoff": "1.5",
                "max_posts_per_batch": 20,
                "max_posts_per_run": 100,
                "hours_lookback": 48,
                "custom_prompt": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T12:00:00Z",
            }
        ]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        with patch("job_finder.db.settings.get_supabase_client", return_value=mock_client):
            from job_finder.db.settings import get_settings

            result = get_settings()

        assert result is not None
        assert result.llm_model_name == "gpt-4o"
        assert result.channels == ["@channel1", "@channel2"]
        assert result.scheduler_enabled is True

    def test_get_settings_empty(self) -> None:
        """Should return None when no settings exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        with patch("job_finder.db.settings.get_supabase_client", return_value=mock_client):
            from job_finder.db.settings import get_settings

            result = get_settings()

        assert result is None


class TestUpsertSettings:
    """Tests for upsert_settings function."""

    def test_upsert_settings_update(self) -> None:
        """Should update existing settings and return SettingsDB."""
        existing_settings = SettingsDB(
            id="123e4567-e89b-12d3-a456-426614174000",
            channels=[],
            scheduler_enabled=False,
            llm_model_name="gpt-4.1-mini",
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "channels": [],
                "scheduler_enabled": False,
                "scheduler_time_utc": None,
                "llm_model_name": "gpt-4o",
                "llm_temperature": "0.5",
                "llm_timeout": 60,
                "llm_retry_max": 2,
                "llm_retry_backoff": "2.0",
                "max_posts_per_batch": 10,
                "max_posts_per_run": 30,
                "hours_lookback": 24,
                "custom_prompt": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T12:00:00Z",
            }
        ]
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_response

        with (
            patch("job_finder.db.settings.get_supabase_client", return_value=mock_client),
            patch("job_finder.db.settings.get_settings", return_value=existing_settings),
        ):
            from job_finder.db.settings import upsert_settings

            update = SettingsUpdate(
                llm_model_name="gpt-4o",
                llm_temperature=Decimal("0.5"),
            )
            result = upsert_settings(update)

        assert result is not None
        assert result.llm_model_name == "gpt-4o"
        mock_client.table.return_value.upsert.assert_called_once()

    def test_upsert_settings_empty_update(self) -> None:
        """Should handle empty update."""
        existing_settings = SettingsDB(
            id="123e4567-e89b-12d3-a456-426614174000",
            channels=[],
            scheduler_enabled=False,
            llm_model_name="gpt-4.1-mini",
        )

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "channels": [],
                "scheduler_enabled": False,
                "scheduler_time_utc": None,
                "llm_model_name": "gpt-4.1-mini",
                "llm_temperature": None,
                "llm_timeout": 60,
                "llm_retry_max": 2,
                "llm_retry_backoff": "2.0",
                "max_posts_per_batch": 10,
                "max_posts_per_run": 30,
                "hours_lookback": 24,
                "custom_prompt": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T12:00:00Z",
            }
        ]
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_response

        with (
            patch("job_finder.db.settings.get_supabase_client", return_value=mock_client),
            patch("job_finder.db.settings.get_settings", return_value=existing_settings),
        ):
            from job_finder.db.settings import upsert_settings

            update = SettingsUpdate()
            result = upsert_settings(update)

        assert result is not None


class TestEnsureSettingsExist:
    """Tests for ensure_settings_exist function."""

    def test_ensure_creates_if_missing(self) -> None:
        """Should create default settings if none exist."""
        mock_client = MagicMock()

        # First call (select) returns empty
        mock_select_response = MagicMock()
        mock_select_response.data = []
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_select_response

        # Second call (insert) returns created settings
        mock_insert_response = MagicMock()
        mock_insert_response.data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "channels": [],
                "scheduler_enabled": False,
                "scheduler_time_utc": None,
                "llm_model_name": "gpt-4.1-mini",
                "llm_temperature": None,
                "llm_timeout": 60,
                "llm_retry_max": 2,
                "llm_retry_backoff": "2.0",
                "max_posts_per_batch": 10,
                "max_posts_per_run": 30,
                "hours_lookback": 24,
                "custom_prompt": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
            }
        ]
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            mock_insert_response
        )

        with patch("job_finder.db.settings.get_supabase_client", return_value=mock_client):
            from job_finder.db.settings import ensure_settings_exist

            result = ensure_settings_exist()

        assert result is not None
        assert result.llm_model_name == "gpt-4.1-mini"
        mock_client.table.return_value.insert.assert_called_once()

    def test_ensure_returns_existing(self) -> None:
        """Should return existing settings without creating."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "channels": ["@ch1"],
                "scheduler_enabled": True,
                "scheduler_time_utc": "10:00",
                "llm_model_name": "gpt-4o",
                "llm_temperature": "0.7",
                "llm_timeout": 120,
                "llm_retry_max": 3,
                "llm_retry_backoff": "1.5",
                "max_posts_per_batch": 20,
                "max_posts_per_run": 100,
                "hours_lookback": 48,
                "custom_prompt": "Custom prompt",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T12:00:00Z",
            }
        ]
        mock_client.table.return_value.select.return_value.limit.return_value.execute.return_value = mock_response

        with patch("job_finder.db.settings.get_supabase_client", return_value=mock_client):
            from job_finder.db.settings import ensure_settings_exist

            result = ensure_settings_exist()

        assert result is not None
        assert result.llm_model_name == "gpt-4o"
        assert result.custom_prompt == "Custom prompt"
        mock_client.table.return_value.insert.assert_not_called()


class TestUpdateSettingsField:
    """Tests for update_settings_field function."""

    def test_update_single_field(self) -> None:
        """Should update single field by name."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "channels": [],
                "scheduler_enabled": False,
                "scheduler_time_utc": None,
                "llm_model_name": "gpt-4o",
                "llm_temperature": None,
                "llm_timeout": 60,
                "llm_retry_max": 2,
                "llm_retry_backoff": "2.0",
                "max_posts_per_batch": 10,
                "max_posts_per_run": 30,
                "hours_lookback": 24,
                "custom_prompt": None,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T12:00:00Z",
            }
        ]
        mock_client.table.return_value.update.return_value.neq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.settings.get_supabase_client", return_value=mock_client):
            from job_finder.db.settings import update_settings_field

            result = update_settings_field("llm_model_name", "gpt-4o")

        assert result is not None
        assert result.llm_model_name == "gpt-4o"
        mock_client.table.return_value.update.assert_called_once_with({"llm_model_name": "gpt-4o"})
