"""Tests for SettingsManager."""

from __future__ import annotations

import time
from decimal import Decimal
from unittest.mock import MagicMock, patch

from job_finder.db.models import SettingsDB


class TestSettingsManager:
    """Tests for SettingsManager class."""

    def test_get_settings_from_db(self) -> None:
        """Should return settings from database when available."""
        db_settings = SettingsDB(
            id="test-id",
            channels=["@channel1", "@channel2"],
            scheduler_enabled=True,
            scheduler_time_utc="09:00",
            llm_model_name="gpt-4o",
            llm_temperature=Decimal("0.7"),
            llm_timeout=120,
            llm_retry_max=3,
            llm_retry_backoff=Decimal("1.5"),
            max_posts_per_batch=20,
            max_posts_per_run=100,
            hours_lookback=48,
            custom_prompt="Custom prompt",
        )

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            settings = manager.get_settings()

        assert settings is not None
        assert settings.llm_model_name == "gpt-4o"
        assert settings.channels == ["@channel1", "@channel2"]

    def test_get_settings_caching(self) -> None:
        """Should cache settings and not call DB repeatedly."""
        db_settings = SettingsDB(
            id="test-id",
            llm_model_name="gpt-4o",
        )

        mock_get_settings = MagicMock(return_value=db_settings)

        with patch("job_finder.settings_manager.get_settings", mock_get_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager(cache_ttl=60)

            # First call should fetch from DB
            manager.get_settings()
            # Second call should use cache
            manager.get_settings()
            # Third call should use cache
            manager.get_settings()

        # Should only be called once due to caching
        assert mock_get_settings.call_count == 1

    def test_cache_expiration(self) -> None:
        """Should refresh cache after TTL expires."""
        db_settings = SettingsDB(
            id="test-id",
            llm_model_name="gpt-4o",
        )

        mock_get_settings = MagicMock(return_value=db_settings)

        with patch("job_finder.settings_manager.get_settings", mock_get_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager(cache_ttl=0.1)  # 100ms TTL

            manager.get_settings()
            time.sleep(0.15)  # Wait for cache to expire
            manager.get_settings()

        # Should be called twice - initial and after expiration
        assert mock_get_settings.call_count == 2

    def test_invalidate_cache(self) -> None:
        """Should clear cache when invalidate_cache is called."""
        db_settings = SettingsDB(
            id="test-id",
            llm_model_name="gpt-4o",
        )

        mock_get_settings = MagicMock(return_value=db_settings)

        with patch("job_finder.settings_manager.get_settings", mock_get_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager(cache_ttl=60)

            manager.get_settings()
            manager.invalidate_cache()
            manager.get_settings()

        assert mock_get_settings.call_count == 2

    def test_get_channels_empty_when_db_unavailable(self) -> None:
        """Should return empty list when DB returns None."""
        with patch("job_finder.settings_manager.get_settings", return_value=None):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            channels = manager.get_channels()

        assert channels == []

    def test_get_channels(self) -> None:
        """Should return channels from settings."""
        db_settings = SettingsDB(
            id="test-id",
            channels=["@ch1", "@ch2"],
        )

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            channels = manager.get_channels()

        assert channels == ["@ch1", "@ch2"]

    def test_get_llm_config(self) -> None:
        """Should return LLM configuration dict."""
        db_settings = SettingsDB(
            id="test-id",
            llm_model_name="gpt-4o",
            llm_temperature=Decimal("0.7"),
            llm_timeout=120,
            llm_retry_max=3,
            llm_retry_backoff=Decimal("1.5"),
        )

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            llm_config = manager.get_llm_config()

        assert llm_config["model_name"] == "gpt-4o"
        assert llm_config["temperature"] == 0.7
        assert llm_config["timeout"] == 120
        assert llm_config["retry_max"] == 3
        assert llm_config["retry_backoff"] == 1.5

    def test_get_custom_prompt(self) -> None:
        """Should return custom prompt if set."""
        db_settings = SettingsDB(
            id="test-id",
            custom_prompt="My custom prompt",
        )

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            prompt = manager.get_custom_prompt()

        assert prompt == "My custom prompt"

    def test_get_custom_prompt_none(self) -> None:
        """Should return None when custom prompt not set."""
        db_settings = SettingsDB(
            id="test-id",
            custom_prompt=None,
        )

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            prompt = manager.get_custom_prompt()

        assert prompt is None

    def test_get_scheduler_config(self) -> None:
        """Should return scheduler configuration."""
        db_settings = SettingsDB(
            id="test-id",
            scheduler_enabled=True,
            scheduler_time_utc="09:30",
        )

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            scheduler = manager.get_scheduler_config()

        assert scheduler["enabled"] is True
        assert scheduler["time_utc"] == "09:30"

    def test_get_processing_limits(self) -> None:
        """Should return processing limit configuration."""
        db_settings = SettingsDB(
            id="test-id",
            max_posts_per_batch=25,
            max_posts_per_run=150,
            hours_lookback=72,
        )

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            limits = manager.get_processing_limits()

        assert limits["max_posts_per_batch"] == 25
        assert limits["max_posts_per_run"] == 150
        assert limits["hours_lookback"] == 72

    def test_is_supabase_available_true(self) -> None:
        """Should return True when settings can be fetched."""
        db_settings = SettingsDB(id="test-id")

        with patch("job_finder.settings_manager.get_settings", return_value=db_settings):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            available = manager.is_supabase_available()

        assert available is True

    def test_is_supabase_available_false(self) -> None:
        """Should return False when settings cannot be fetched."""
        with patch("job_finder.settings_manager.get_settings", return_value=None):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            available = manager.is_supabase_available()

        assert available is False

    def test_get_llm_defaults_when_db_unavailable(self) -> None:
        """Should return default values when DB is unavailable."""
        with patch("job_finder.settings_manager.get_settings", return_value=None):
            from job_finder.settings_manager import SettingsManager

            manager = SettingsManager()
            model = manager.get_llm_model_name()
            temp = manager.get_llm_temperature()
            timeout = manager.get_llm_timeout()
            retry_config = manager.get_llm_retry_config()
            limits = manager.get_processing_limits()

        assert model == "gpt-4.1-mini"
        assert temp is None
        assert timeout == 60
        assert retry_config == {"retry_max": 2, "retry_backoff": 2.0}
        assert limits == {
            "max_posts_per_batch": 10,
            "max_posts_per_run": 30,
            "hours_lookback": 24,
        }
