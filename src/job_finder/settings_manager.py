"""Settings manager with caching.

This module provides a SettingsManager class that handles:
- Fetching settings from Supabase database
- Caching settings with configurable TTL
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, TypedDict, cast

from job_finder.db.models import SettingsDB
from job_finder.db.settings import get_settings

logger = logging.getLogger(__name__)

# Default cache TTL in seconds
DEFAULT_CACHE_TTL = 60.0


class SchedulerConfigDict(TypedDict):
    enabled: bool
    time_utc: Optional[str]


class JobSpyConfigDict(TypedDict):
    sites: List[str]
    location: Optional[str]
    country: str
    results_wanted: int
    hours_old: int
    is_remote: Optional[bool]
    job_type: Optional[str]


class SettingsManagerError(Exception):
    """Error raised when settings cannot be fetched."""

    pass


class SettingsManager:
    """Manager for bot settings with caching.

    Provides a unified interface to access settings from Supabase database.

    Attributes:
        cache_ttl: Time-to-live for cached settings in seconds
    """

    def __init__(self, cache_ttl: float = DEFAULT_CACHE_TTL) -> None:
        """Initialize settings manager.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 60)
        """
        self.cache_ttl = cache_ttl
        self._cache: Optional[SettingsDB] = None
        self._cache_time: float = 0

    def _is_cache_valid(self) -> bool:
        """Check if cached settings are still valid."""
        if self._cache is None:
            return False
        return (time.time() - self._cache_time) < self.cache_ttl

    def invalidate_cache(self) -> None:
        """Clear the settings cache."""
        self._cache = None
        self._cache_time = 0
        logger.debug("Settings cache invalidated")

    def get_settings(self) -> Optional[SettingsDB]:
        """Get current settings with caching.

        Returns cached settings if valid, otherwise fetches from DB.

        Returns:
            SettingsDB if available, None if DB unavailable
        """
        if self._is_cache_valid():
            return self._cache

        try:
            settings = get_settings()
            if settings:
                self._cache = settings
                self._cache_time = time.time()
                logger.debug("Settings loaded from database")
            return settings
        except Exception as e:
            logger.warning("Failed to fetch settings from DB: %s", e)
            return self._cache  # Return stale cache if available

    def is_supabase_available(self) -> bool:
        """Check if Supabase settings are available.

        Returns:
            True if settings can be fetched from DB
        """
        settings = self.get_settings()
        return settings is not None

    # --- Channel settings ---

    def get_channels(self) -> List[str]:
        """Get list of Telegram channels to monitor.

        Returns:
            List of channel usernames
        """
        settings = self.get_settings()
        if settings and settings.channels:
            return settings.channels
        return []

    # --- LLM settings ---

    def get_llm_model_name(self) -> str:
        """Get LLM model name.

        Returns:
            Model name string
        """
        settings = self.get_settings()
        if settings:
            return settings.llm_model_name
        return "gpt-4.1-mini"

    def get_llm_temperature(self) -> Optional[float]:
        """Get LLM temperature setting.

        Returns:
            Temperature float or None for API default
        """
        settings = self.get_settings()
        if settings and settings.llm_temperature is not None:
            return float(settings.llm_temperature)
        return None

    def get_llm_timeout(self) -> int:
        """Get LLM request timeout in seconds.

        Returns:
            Timeout in seconds
        """
        settings = self.get_settings()
        if settings:
            return settings.llm_timeout
        return 60

    def get_llm_retry_config(self) -> Dict[str, Any]:
        """Get LLM retry configuration.

        Returns:
            Dict with retry_max and retry_backoff
        """
        settings = self.get_settings()
        if settings:
            return {
                "retry_max": settings.llm_retry_max,
                "retry_backoff": float(settings.llm_retry_backoff),
            }
        return {"retry_max": 2, "retry_backoff": 2.0}

    def get_llm_config(self) -> Dict[str, Any]:
        """Get complete LLM configuration.

        Returns:
            Dict with all LLM settings
        """
        retry_config = self.get_llm_retry_config()
        return {
            "model_name": self.get_llm_model_name(),
            "temperature": self.get_llm_temperature(),
            "timeout": self.get_llm_timeout(),
            "retry_max": retry_config["retry_max"],
            "retry_backoff": retry_config["retry_backoff"],
        }

    # --- Custom prompt ---

    def get_custom_prompt(self) -> Optional[str]:
        """Get custom system prompt if set.

        Returns:
            Custom prompt string or None to use default
        """
        settings = self.get_settings()
        if settings:
            return settings.custom_prompt
        return None

    # --- Scheduler settings ---

    def get_scheduler_config(self) -> SchedulerConfigDict:
        """Get scheduler configuration.

        Returns:
            Dict with enabled and time_utc
        """
        settings = self.get_settings()
        if settings:
            return {
                "enabled": settings.scheduler_enabled,
                "time_utc": settings.scheduler_time_utc,
            }
        return {"enabled": False, "time_utc": None}

    def is_scheduler_enabled(self) -> bool:
        """Check if scheduler is enabled.

        Returns:
            True if scheduler should run
        """
        return self.get_scheduler_config()["enabled"]

    def get_scheduler_time(self) -> Optional[str]:
        """Get scheduler time in HH:MM format.

        Returns:
            Time string or None
        """
        return self.get_scheduler_config()["time_utc"]

    # --- Processing limits ---

    def get_processing_limits(self) -> Dict[str, int]:
        """Get processing limit configuration.

        Returns:
            Dict with max_posts_per_batch, max_posts_per_run, hours_lookback
        """
        settings = self.get_settings()
        if settings:
            return {
                "max_posts_per_batch": settings.max_posts_per_batch,
                "max_posts_per_run": settings.max_posts_per_run,
                "hours_lookback": settings.hours_lookback,
            }
        return {
            "max_posts_per_batch": 10,
            "max_posts_per_run": 30,
            "hours_lookback": 24,
        }

    def get_max_posts_per_batch(self) -> int:
        """Get maximum posts per LLM batch.

        Returns:
            Batch size limit
        """
        return self.get_processing_limits()["max_posts_per_batch"]

    def get_max_posts_per_run(self) -> int:
        """Get maximum posts per run.

        Returns:
            Run limit
        """
        return self.get_processing_limits()["max_posts_per_run"]

    def get_hours_lookback(self) -> int:
        """Get hours lookback for scraping.

        Returns:
            Hours to look back
        """
        return self.get_processing_limits()["hours_lookback"]

    # --- JobSpy settings ---

    def get_jobspy_enabled(self) -> bool:
        """Check if JobSpy integration is enabled.

        Returns:
            True if JobSpy pipeline should run
        """
        settings = self.get_settings()
        if settings:
            return settings.jobspy_enabled
        return False

    def get_jobspy_search_terms(self) -> List[str]:
        """Get JobSpy search terms.

        Returns:
            List of search term strings
        """
        settings = self.get_settings()
        if settings and settings.jobspy_search_terms:
            return settings.jobspy_search_terms
        return ["Product Manager"]

    def get_jobspy_config(self) -> Optional[JobSpyConfigDict]:
        """Get complete JobSpy configuration.

        Returns:
            Dict with all JobSpy settings, or None if disabled
        """
        settings = self.get_settings()
        if not settings or not settings.jobspy_enabled:
            return None

        return cast(
            JobSpyConfigDict,
            {
                "sites": settings.jobspy_sites or ["indeed", "google"],
                "location": settings.jobspy_location,
                "country": settings.jobspy_country or "USA",
                "results_wanted": settings.jobspy_results_wanted or 20,
                "hours_old": settings.jobspy_hours_old or 24,
                "is_remote": settings.jobspy_is_remote,
                "job_type": settings.jobspy_job_type,
            },
        )


# Global singleton instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get or create the global SettingsManager instance.

    Returns:
        Global SettingsManager singleton
    """
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def init_settings_manager() -> SettingsManager:
    """Initialize the global SettingsManager.

    Returns:
        Initialized SettingsManager
    """
    global _settings_manager
    _settings_manager = SettingsManager()
    return _settings_manager
