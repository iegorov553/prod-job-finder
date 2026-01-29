"""Pydantic models for database entities.

These models define the schema for database tables and provide
validation for data going in and out of Supabase.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# Type aliases for better readability
AnalysisStatus = Literal["pending", "completed", "failed"]
VacancyStatus = Literal["new", "saved", "applied", "interview", "rejected", "offer"]
Seniority = Literal["junior", "middle", "senior", "lead", "head", "other"]
RemoteType = Literal["remote", "hybrid", "onsite", "unknown"]
Language = Literal["en", "ru", "other"]


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


class PostAnalysisResult(BaseModel):
    """Result of LLM analysis for a single post.

    One post can contain multiple vacancies, so this model
    wraps the post_id with a list of extracted vacancies.
    """

    post_id: int
    vacancies: List[VacancyFromLLM] = Field(default_factory=list)


# Re-export for easier imports
__all__ = [
    "AnalysisStatus",
    "VacancyStatus",
    "Seniority",
    "RemoteType",
    "Language",
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
]
