"""Digest building from database records."""

from __future__ import annotations

from typing import Iterable, List

from job_finder import digest
from job_finder.db.posts import get_post_by_id
from job_finder.db.vacancies import get_new_relevant_vacancies
from job_finder.models import VacancyNormalized


def _normalize_for_digest(vacancies: Iterable) -> List[VacancyNormalized]:
    normalized: list[VacancyNormalized] = []
    for v in vacancies:
        post = get_post_by_id(v.post_id)
        source_channel = post.channel if post else ""
        source_link = post.source_link if post else None
        post_date = post.telegram_date if post else None

        normalized.append(
            VacancyNormalized(
                id=v.id,
                is_relevant=v.is_relevant,
                relevance_reason=v.relevance_reason or "",
                title=v.title,
                company=v.company,
                industry=v.industry,
                level=v.level,
                role=None,
                location=v.location,
                remote_type=v.remote_type,
                salary_min_usd=float(v.salary_min_usd) if v.salary_min_usd else None,
                salary_max_usd=float(v.salary_max_usd) if v.salary_max_usd else None,
                salary_raw=v.salary_raw,
                language=v.language or "other",
                source_channel=source_channel,
                source_message_id=v.post_id,
                source_link=source_link,
                apply_link=v.apply_link,
                raw_snippet=v.raw_snippet or "",
                post_date=post_date,
            )
        )
    return normalized


def build_digest_from_db(limit: int = 100) -> str:
    relevant_vacancies = get_new_relevant_vacancies(limit=limit)
    normalized_for_digest = _normalize_for_digest(relevant_vacancies)
    return digest.build_digest(normalized_for_digest)
