"""Pydantic models for database entities.

These models define the schema for database tables and provide
validation for data going in and out of Supabase.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Type aliases for better readability
AnalysisStatus = Literal["pending", "completed", "failed"]
VacancyStatus = Literal["new", "saved", "applied", "interview", "rejected", "offer"]
Seniority = Literal["junior", "middle", "senior", "lead", "head", "other"]
RemoteType = Literal["remote", "hybrid", "onsite", "unknown"]
Language = Literal["en", "ru", "other"]
RunStatus = Literal["running", "success", "failed"]
LinkType = Literal[
    "apply_direct",
    "job_board_post",
    "social_post",
    "company_careers",
    "job_description",
    "recruiter_contact",
    "company_website",
    "other",
]


class VacancyLink(BaseModel):
    """Structured link metadata for vacancy-related URLs."""

    url: str
    type: LinkType = "other"


class ChannelStateDB(BaseModel):
    """Model for channel_states table."""

    model_config = ConfigDict(from_attributes=True)

    channel: str
    last_message_id: Optional[int] = None
    updated_at: Optional[datetime] = None


class ChannelStateCreate(BaseModel):
    """Model for creating a new channel state."""

    channel: str
    last_message_id: Optional[int] = None


class PostDB(BaseModel):
    """Model for posts table (full record from DB)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_id: int
    channel: str
    telegram_date: datetime
    text_full: str
    source_link: Optional[str] = None
    links: List[str] = Field(default_factory=list)
    analyzed_at: Optional[datetime] = None
    analysis_status: AnalysisStatus = "pending"
    vacancies_count: int = 0
    created_at: Optional[datetime] = None


class PostCreate(BaseModel):
    """Model for creating a new post."""

    telegram_id: int
    channel: str
    telegram_date: datetime
    text_full: str
    source_link: Optional[str] = None
    links: List[str] = Field(default_factory=list)


class PostUpdate(BaseModel):
    """Model for updating a post after analysis."""

    analyzed_at: Optional[datetime] = None
    analysis_status: Optional[AnalysisStatus] = None
    vacancies_count: Optional[int] = None


class VacancyDB(BaseModel):
    """Model for vacancies table (full record from DB)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    level: Optional[Seniority] = None
    location: Optional[str] = None
    remote_type: RemoteType = "unknown"
    salary_min_usd: Optional[Decimal] = None
    salary_max_usd: Optional[Decimal] = None
    salary_raw: Optional[str] = None
    language: Optional[Language] = None
    is_relevant: bool = False
    relevance_reason: Optional[str] = None
    status: VacancyStatus = "new"
    apply_link: Optional[str] = None
    links_json: List[VacancyLink] = Field(default_factory=list)
    notes: Optional[str] = None
    cover_letter: Optional[str] = None
    raw_snippet: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VacancyCreate(BaseModel):
    """Model for creating a new vacancy."""

    post_id: int
    title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    level: Optional[Seniority] = None
    location: Optional[str] = None
    remote_type: RemoteType = "unknown"
    salary_min_usd: Optional[Decimal] = None
    salary_max_usd: Optional[Decimal] = None
    salary_raw: Optional[str] = None
    language: Optional[Language] = None
    is_relevant: bool = False
    relevance_reason: Optional[str] = None
    raw_snippet: Optional[str] = None
    apply_link: Optional[str] = None
    links_json: List[VacancyLink] = Field(default_factory=list)


class VacancyUpdate(BaseModel):
    """Model for updating a vacancy."""

    status: Optional[VacancyStatus] = None
    notes: Optional[str] = None
    cover_letter: Optional[str] = None
    apply_link: Optional[str] = None


class VacancyFromLLM(BaseModel):
    """Vacancy data as returned by LLM.

    This is the raw structure from LLM response before
    being converted to VacancyCreate for database insertion.
    """

    is_relevant: bool = False
    relevance_reason: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    level: Optional[Seniority] = None
    location: Optional[str] = None
    remote_type: Optional[RemoteType] = None
    salary_min_usd: Optional[float] = None
    salary_max_usd: Optional[float] = None
    salary_raw: Optional[str] = None
    language: Optional[Language] = None
    raw_snippet: Optional[str] = None
    apply_link: Optional[str] = None
    links_json: List[VacancyLink] = Field(default_factory=list)


class PostAnalysisResult(BaseModel):
    """Result of LLM analysis for a single post.

    One post can contain multiple vacancies, so this model
    wraps the post_id with a list of extracted vacancies.
    """

    post_id: int
    vacancies: List[VacancyFromLLM] = Field(default_factory=list)


class SettingsDB(BaseModel):
    """Model for settings table (full record from DB).

    Contains all dynamic bot configuration stored in Supabase.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str  # UUID as string
    channels: List[str] = Field(default_factory=list)
    scheduler_enabled: bool = False
    scheduler_time_utc: Optional[str] = None  # HH:MM format
    llm_model_name: str = "gpt-4.1-mini"
    llm_temperature: Optional[Decimal] = None
    llm_timeout: int = 60
    llm_retry_max: int = 2
    llm_retry_backoff: Decimal = Decimal("2.0")
    max_posts_per_batch: int = 10
    max_posts_per_run: int = 30
    hours_lookback: int = 24
    custom_prompt: str  # Required, stored in database
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("channels", mode="before")
    @classmethod
    def parse_channels(cls, v: Any) -> List[str]:
        """Parse JSONB channels field."""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        return []

    @field_validator("scheduler_time_utc")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate HH:MM time format."""
        if v is None:
            return None
        import re

        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("Time must be in HH:MM format (00:00-23:59)")
        return v


class SettingsUpdate(BaseModel):
    """Model for updating settings.

    All fields are optional - only provided fields will be updated.
    Includes validation for acceptable value ranges.
    """

    channels: Optional[List[str]] = None
    scheduler_enabled: Optional[bool] = None
    scheduler_time_utc: Optional[str] = None
    llm_model_name: Optional[str] = None
    llm_temperature: Optional[Decimal] = None
    llm_timeout: Optional[int] = None
    llm_retry_max: Optional[int] = None
    llm_retry_backoff: Optional[Decimal] = None
    max_posts_per_batch: Optional[int] = None
    max_posts_per_run: Optional[int] = None
    hours_lookback: Optional[int] = None
    custom_prompt: Optional[str] = None

    @field_validator("scheduler_time_utc")
    @classmethod
    def validate_time_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate HH:MM time format."""
        if v is None:
            return None
        import re

        if not re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", v):
            raise ValueError("Time must be in HH:MM format (00:00-23:59)")
        return v

    @field_validator("llm_temperature")
    @classmethod
    def validate_temperature(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate temperature range (0.0 - 2.0)."""
        if v is None:
            return None
        if v < 0 or v > 2:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @field_validator("llm_timeout")
    @classmethod
    def validate_timeout(cls, v: Optional[int]) -> Optional[int]:
        """Validate timeout range (10 - 300 seconds)."""
        if v is None:
            return None
        if v < 10 or v > 300:
            raise ValueError("Timeout must be between 10 and 300 seconds")
        return v

    @field_validator("max_posts_per_batch")
    @classmethod
    def validate_batch(cls, v: Optional[int]) -> Optional[int]:
        """Validate batch size range (1 - 50)."""
        if v is None:
            return None
        if v < 1 or v > 50:
            raise ValueError("Batch size must be between 1 and 50")
        return v

    @field_validator("max_posts_per_run")
    @classmethod
    def validate_run_limit(cls, v: Optional[int]) -> Optional[int]:
        """Validate run limit range (1 - 500)."""
        if v is None:
            return None
        if v < 1 or v > 500:
            raise ValueError("Run limit must be between 1 and 500")
        return v

    @field_validator("hours_lookback")
    @classmethod
    def validate_lookback(cls, v: Optional[int]) -> Optional[int]:
        """Validate lookback range (1 - 168 hours / 1 week)."""
        if v is None:
            return None
        if v < 1 or v > 168:
            raise ValueError("Lookback must be between 1 and 168 hours")
        return v

    @field_validator("custom_prompt")
    @classmethod
    def validate_prompt_length(cls, v: Optional[str]) -> Optional[str]:
        """Validate custom prompt length (max 10000 chars)."""
        if v is None:
            return None
        if len(v) > 10000:
            raise ValueError("Custom prompt must be at most 10000 characters")
        return v

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database update, excluding None values."""
        data = {}
        for field_name, field_value in self:
            if field_value is not None:
                # Convert Decimal to float for JSON serialization
                if isinstance(field_value, Decimal):
                    data[field_name] = float(field_value)
                else:
                    data[field_name] = field_value
        return data


class RunDB(BaseModel):
    """Model for runs table (full record from DB)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: RunStatus
    digest_md: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class RunCreate(BaseModel):
    """Model for creating a run entry."""

    status: RunStatus = "running"


class RunUpdate(BaseModel):
    """Model for updating a run entry."""

    status: Optional[RunStatus] = None
    digest_md: Optional[str] = None
    error: Optional[str] = None
    finished_at: Optional[datetime] = None


# Re-export for easier imports
__all__ = [
    "AnalysisStatus",
    "VacancyStatus",
    "Seniority",
    "RemoteType",
    "Language",
    "RunStatus",
    "LinkType",
    "VacancyLink",
    "ChannelStateDB",
    "ChannelStateCreate",
    "PostDB",
    "PostCreate",
    "PostUpdate",
    "VacancyDB",
    "VacancyCreate",
    "VacancyUpdate",
    "PostAnalysisResult",
    "VacancyFromLLM",
    "SettingsDB",
    "SettingsUpdate",
    "RunDB",
    "RunCreate",
    "RunUpdate",
]
