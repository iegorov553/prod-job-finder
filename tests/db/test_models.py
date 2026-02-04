"""Tests for database models."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from job_finder.db.models import SettingsDB, SettingsUpdate

# Test constant for required custom_prompt field
TEST_PROMPT = "Test system prompt for job analysis."


class TestSettingsDB:
    """Tests for SettingsDB model."""

    def test_create_with_required_fields(self) -> None:
        """Should create SettingsDB with required fields and defaults."""
        settings = SettingsDB(
            id="123e4567-e89b-12d3-a456-426614174000",
            custom_prompt=TEST_PROMPT,
        )

        assert settings.id == "123e4567-e89b-12d3-a456-426614174000"
        assert settings.channels == []
        assert settings.scheduler_enabled is False
        assert settings.scheduler_time_utc is None
        assert settings.llm_model_name == "gpt-4.1-mini"
        assert settings.llm_temperature is None
        assert settings.llm_timeout == 60
        assert settings.llm_retry_max == 2
        assert settings.llm_retry_backoff == Decimal("2.0")
        assert settings.max_posts_per_batch == 10
        assert settings.max_posts_per_run == 30
        assert settings.hours_lookback == 24
        assert settings.custom_prompt == TEST_PROMPT

    def test_custom_prompt_required(self) -> None:
        """Should require custom_prompt field."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsDB(id="test-id")
        assert "custom_prompt" in str(exc_info.value)

    def test_create_from_db_response(self) -> None:
        """Should parse response from Supabase correctly."""
        db_data = {
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
            "custom_prompt": "Custom system prompt",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T12:00:00Z",
        }
        settings = SettingsDB(**db_data)

        assert settings.channels == ["@channel1", "@channel2"]
        assert settings.scheduler_enabled is True
        assert settings.scheduler_time_utc == "09:00"
        assert settings.llm_model_name == "gpt-4o"
        assert settings.llm_temperature == Decimal("0.7")
        assert settings.max_posts_per_batch == 20
        assert settings.custom_prompt == "Custom system prompt"

    def test_parse_channels_from_jsonb(self) -> None:
        """Should parse JSONB channels field."""
        settings = SettingsDB(
            id="test-id",
            channels=["@ch1", "@ch2"],
            custom_prompt=TEST_PROMPT,
        )
        assert settings.channels == ["@ch1", "@ch2"]

    def test_parse_channels_none(self) -> None:
        """Should handle None channels as empty list."""
        settings = SettingsDB(
            id="test-id",
            channels=None,  # type: ignore[arg-type]
            custom_prompt=TEST_PROMPT,
        )
        assert settings.channels == []

    def test_validate_time_format_valid(self) -> None:
        """Should accept valid HH:MM format."""
        settings = SettingsDB(id="test", scheduler_time_utc="09:30", custom_prompt=TEST_PROMPT)
        assert settings.scheduler_time_utc == "09:30"

        settings = SettingsDB(id="test", scheduler_time_utc="00:00", custom_prompt=TEST_PROMPT)
        assert settings.scheduler_time_utc == "00:00"

        settings = SettingsDB(id="test", scheduler_time_utc="23:59", custom_prompt=TEST_PROMPT)
        assert settings.scheduler_time_utc == "23:59"

    def test_validate_time_format_invalid(self) -> None:
        """Should reject invalid time formats."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsDB(
                id="test", scheduler_time_utc="9:30", custom_prompt=TEST_PROMPT
            )  # Missing leading zero
        assert "HH:MM" in str(exc_info.value)

        with pytest.raises(ValidationError):
            SettingsDB(
                id="test", scheduler_time_utc="24:00", custom_prompt=TEST_PROMPT
            )  # Invalid hour

        with pytest.raises(ValidationError):
            SettingsDB(
                id="test", scheduler_time_utc="12:60", custom_prompt=TEST_PROMPT
            )  # Invalid minute

        with pytest.raises(ValidationError):
            SettingsDB(
                id="test", scheduler_time_utc="12:00:00", custom_prompt=TEST_PROMPT
            )  # Includes seconds


class TestSettingsUpdate:
    """Tests for SettingsUpdate model."""

    def test_create_empty(self) -> None:
        """Should create update with no fields."""
        update = SettingsUpdate()
        assert update.channels is None
        assert update.llm_model_name is None

    def test_create_partial(self) -> None:
        """Should create update with only specified fields."""
        update = SettingsUpdate(llm_model_name="gpt-4o", llm_timeout=120)
        assert update.llm_model_name == "gpt-4o"
        assert update.llm_timeout == 120
        assert update.channels is None

    def test_validate_temperature_valid(self) -> None:
        """Should accept valid temperature values."""
        update = SettingsUpdate(llm_temperature=Decimal("0.0"))
        assert update.llm_temperature == Decimal("0.0")

        update = SettingsUpdate(llm_temperature=Decimal("1.0"))
        assert update.llm_temperature == Decimal("1.0")

        update = SettingsUpdate(llm_temperature=Decimal("2.0"))
        assert update.llm_temperature == Decimal("2.0")

    def test_validate_temperature_invalid(self) -> None:
        """Should reject temperature outside 0.0-2.0 range."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsUpdate(llm_temperature=Decimal("-0.1"))
        assert "0.0 and 2.0" in str(exc_info.value)

        with pytest.raises(ValidationError):
            SettingsUpdate(llm_temperature=Decimal("2.1"))

    def test_validate_timeout_valid(self) -> None:
        """Should accept valid timeout values (10-300)."""
        update = SettingsUpdate(llm_timeout=10)
        assert update.llm_timeout == 10

        update = SettingsUpdate(llm_timeout=300)
        assert update.llm_timeout == 300

    def test_validate_timeout_invalid(self) -> None:
        """Should reject timeout outside 10-300 range."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsUpdate(llm_timeout=9)
        assert "10 and 300" in str(exc_info.value)

        with pytest.raises(ValidationError):
            SettingsUpdate(llm_timeout=301)

    def test_validate_batch_size_valid(self) -> None:
        """Should accept valid batch size values (1-50)."""
        update = SettingsUpdate(max_posts_per_batch=1)
        assert update.max_posts_per_batch == 1

        update = SettingsUpdate(max_posts_per_batch=50)
        assert update.max_posts_per_batch == 50

    def test_validate_batch_size_invalid(self) -> None:
        """Should reject batch size outside 1-50 range."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsUpdate(max_posts_per_batch=0)
        assert "1 and 50" in str(exc_info.value)

        with pytest.raises(ValidationError):
            SettingsUpdate(max_posts_per_batch=51)

    def test_validate_run_limit_valid(self) -> None:
        """Should accept valid run limit values (1-500)."""
        update = SettingsUpdate(max_posts_per_run=1)
        assert update.max_posts_per_run == 1

        update = SettingsUpdate(max_posts_per_run=500)
        assert update.max_posts_per_run == 500

    def test_validate_run_limit_invalid(self) -> None:
        """Should reject run limit outside 1-500 range."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsUpdate(max_posts_per_run=0)
        assert "1 and 500" in str(exc_info.value)

        with pytest.raises(ValidationError):
            SettingsUpdate(max_posts_per_run=501)

    def test_validate_lookback_valid(self) -> None:
        """Should accept valid lookback values (1-168 hours)."""
        update = SettingsUpdate(hours_lookback=1)
        assert update.hours_lookback == 1

        update = SettingsUpdate(hours_lookback=168)
        assert update.hours_lookback == 168

    def test_validate_lookback_invalid(self) -> None:
        """Should reject lookback outside 1-168 range."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsUpdate(hours_lookback=0)
        assert "1 and 168" in str(exc_info.value)

        with pytest.raises(ValidationError):
            SettingsUpdate(hours_lookback=169)

    def test_validate_custom_prompt_valid(self) -> None:
        """Should accept prompt up to 10000 characters."""
        update = SettingsUpdate(custom_prompt="Short prompt")
        assert update.custom_prompt == "Short prompt"

        update = SettingsUpdate(custom_prompt="x" * 10000)
        assert len(update.custom_prompt) == 10000

    def test_validate_custom_prompt_too_long(self) -> None:
        """Should reject prompt exceeding 10000 characters."""
        with pytest.raises(ValidationError) as exc_info:
            SettingsUpdate(custom_prompt="x" * 10001)
        assert "10000" in str(exc_info.value)

    def test_to_db_dict_excludes_none(self) -> None:
        """Should exclude None values from dict."""
        update = SettingsUpdate(llm_model_name="gpt-4o", llm_timeout=120)
        db_dict = update.to_db_dict()

        assert db_dict == {"llm_model_name": "gpt-4o", "llm_timeout": 120}
        assert "channels" not in db_dict

    def test_to_db_dict_converts_decimal(self) -> None:
        """Should convert Decimal to float for JSON serialization."""
        update = SettingsUpdate(
            llm_temperature=Decimal("0.7"),
            llm_retry_backoff=Decimal("1.5"),
        )
        db_dict = update.to_db_dict()

        assert db_dict["llm_temperature"] == 0.7
        assert db_dict["llm_retry_backoff"] == 1.5
        assert isinstance(db_dict["llm_temperature"], float)

    def test_to_db_dict_empty_update(self) -> None:
        """Should return empty dict for empty update."""
        update = SettingsUpdate()
        assert update.to_db_dict() == {}
