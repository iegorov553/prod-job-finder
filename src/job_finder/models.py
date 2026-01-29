from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Optional

Seniority = Literal["junior", "middle", "senior", "lead", "head", "other"]
RemoteType = Literal["remote", "hybrid", "onsite", "unknown"]
Language = Literal["en", "ru", "other"]


@dataclass
class RawPost:
    id: int
    channel: str
    date: str
    text: str
    links: List[str]
    source_link: Optional[str]


@dataclass
class VacancyNormalized:
    id: int
    is_relevant: bool
    relevance_reason: str

    title: Optional[str]
    company: Optional[str]
    industry: Optional[str]
    level: Optional[Seniority]
    role: Optional[str]
    location: Optional[str]
    remote_type: Optional[RemoteType]

    salary_min_usd: Optional[float]
    salary_max_usd: Optional[float]
    salary_raw: Optional[str]

    language: Language

    source_channel: str
    source_message_id: int
    source_link: Optional[str]
    apply_link: Optional[str]

    raw_snippet: str
