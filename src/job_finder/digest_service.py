"""Digest building from database records."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, List, Optional

from job_finder import digest
from job_finder.db.vacancies import get_new_relevant_vacancies
from job_finder.models import VacancyNormalized


def _get_post_info(post_id: int) -> tuple[str, Optional[str], Optional[datetime]]:
    """Fetch Telegram post info for digest normalization."""
    from job_finder.db.posts import get_post_by_id

    post = get_post_by_id(post_id)
    if post:
        return post.channel, post.source_link, post.telegram_date
    return "", None, None


def _get_jobspy_info(jobspy_job_id: int) -> tuple[str, Optional[str], Optional[datetime]]:
    """Fetch JobSpy job info for digest normalization."""
    from job_finder.db.jobspy_jobs import get_jobspy_job_by_id

    job = get_jobspy_job_by_id(jobspy_job_id)
    if job:
        date_posted = None
        if job.date_posted:
            try:
                date_posted = datetime.fromisoformat(job.date_posted)
            except (ValueError, TypeError):
                pass
        return job.site, job.job_url, date_posted
    return "jobspy", None, None


def _normalize_for_digest(vacancies: Iterable) -> List[VacancyNormalized]:
    normalized: list[VacancyNormalized] = []
    for v in vacancies:
        source_type = getattr(v, "source_type", "telegram")

        if source_type == "jobspy" and getattr(v, "jobspy_job_id", None):
            source_channel, source_link, post_date = _get_jobspy_info(v.jobspy_job_id)
        elif v.post_id:
            source_channel, source_link, post_date = _get_post_info(v.post_id)
        else:
            source_channel, source_link, post_date = "", None, None

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
                source_message_id=v.post_id or 0,
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
