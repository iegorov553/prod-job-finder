"""JobSpy pipeline orchestration.

Runs JobSpy searches, deduplicates results, stores raw jobs
in jobspy_jobs table, and creates vacancy records.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, List

from job_finder.db.jobspy_jobs import create_jobspy_jobs_batch, get_existing_job_urls
from job_finder.db.models import JobSpyJobCreate, JobSpyJobDB, VacancyCreate, VacancyLink
from job_finder.db.vacancies import create_vacancies_batch
from job_finder.jobspy_scraper import JobSpyRawResult, JobSpySearchConfig, scrape_jobspy

if TYPE_CHECKING:
    from job_finder.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


@dataclass
class JobSpyPipelineResult:
    """Summary of a JobSpy pipeline run."""

    total_scraped: int = 0
    new_jobs: int = 0
    duplicates_skipped: int = 0
    vacancies_created: int = 0
    errors: List[str] = field(default_factory=list)


def _jobspy_to_vacancy(job: JobSpyJobDB) -> VacancyCreate:
    """Convert a JobSpyJobDB record to a VacancyCreate for the vacancies table.

    JobSpy results are pre-structured (title, company, salary, URL),
    so they skip LLM analysis and go directly into vacancies.

    Args:
        job: Stored job record from jobspy_jobs table

    Returns:
        VacancyCreate ready for insertion
    """
    remote_type = "remote" if job.is_remote else "unknown"

    # Truncate description for raw_snippet (max 500 chars)
    raw_snippet = None
    if job.description:
        raw_snippet = job.description[:500]

    # Build salary_raw from min/max + currency
    salary_raw = None
    if job.salary_min or job.salary_max:
        parts = []
        currency = job.salary_currency or "USD"
        if job.salary_min:
            parts.append(str(job.salary_min))
        if job.salary_max:
            parts.append(str(job.salary_max))
        salary_raw = f"{currency} {' - '.join(parts)}"

    # Convert salary to USD (assuming already USD for US jobs)
    salary_min_usd = job.salary_min if job.salary_min else None
    salary_max_usd = job.salary_max if job.salary_max else None

    links_json = [VacancyLink(url=job.job_url, type="job_board_post")]

    return VacancyCreate(
        post_id=None,
        source_type="jobspy",
        jobspy_job_id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        remote_type=remote_type,
        salary_min_usd=Decimal(str(salary_min_usd)) if salary_min_usd else None,
        salary_max_usd=Decimal(str(salary_max_usd)) if salary_max_usd else None,
        salary_raw=salary_raw,
        language="en",
        is_relevant=True,
        relevance_reason=f"Matched search term on {job.site}",
        apply_link=job.job_url,
        raw_snippet=raw_snippet,
        links_json=links_json,
    )


def run_jobspy_pipeline(settings_manager: SettingsManager) -> JobSpyPipelineResult:
    """Run the full JobSpy pipeline.

    Steps:
    1. Read JobSpy config from settings
    2. For each search_term: run scrape_jobspy()
    3. Deduplicate by job_url via DB lookup
    4. Insert new jobs into jobspy_jobs table
    5. Convert jobs to vacancies
    6. Insert vacancies into vacancies table

    Args:
        settings_manager: Settings manager with JobSpy config

    Returns:
        Pipeline result with statistics
    """
    result = JobSpyPipelineResult()

    config = settings_manager.get_jobspy_config()
    if config is None:
        logger.info("JobSpy is disabled or not configured")
        return result

    search_terms = settings_manager.get_jobspy_search_terms()
    all_raw_results: List[JobSpyRawResult] = []

    # Run searches for each term
    for term in search_terms:
        search_config = JobSpySearchConfig(
            sites=config["sites"],
            search_term=term,
            location=config.get("location"),
            country=config.get("country", "USA"),
            results_wanted=config.get("results_wanted", 20),
            hours_old=config.get("hours_old", 24),
            is_remote=config.get("is_remote"),
            job_type=config.get("job_type"),
        )
        raw_results = scrape_jobspy(search_config)
        all_raw_results.extend(raw_results)

    result.total_scraped = len(all_raw_results)

    if not all_raw_results:
        logger.info("JobSpy: no results from any search term")
        return result

    # Deduplicate by job_url within batch
    seen_urls: dict[str, JobSpyRawResult] = {}
    for r in all_raw_results:
        if r.job_url not in seen_urls:
            seen_urls[r.job_url] = r
    unique_results = list(seen_urls.values())

    # Check which URLs already exist in DB
    all_urls = [r.job_url for r in unique_results]
    existing_urls = get_existing_job_urls(all_urls)
    new_results = [r for r in unique_results if r.job_url not in existing_urls]
    result.duplicates_skipped = len(unique_results) - len(new_results)

    if not new_results:
        logger.info("JobSpy: all %d results already in DB", len(unique_results))
        return result

    # Create jobspy_jobs records
    jobs_to_create = [
        JobSpyJobCreate(
            site=r.site,
            job_url=r.job_url,
            title=r.title,
            company=r.company,
            location=r.location,
            description=r.description,
            date_posted=r.date_posted,
            salary_min=r.salary_min,
            salary_max=r.salary_max,
            salary_currency=r.salary_currency,
            job_type=r.job_type,
            is_remote=r.is_remote,
            search_term=r.raw_data.get("search_term") or search_terms[0] if search_terms else None,
            raw_data=r.raw_data,
        )
        for r in new_results
    ]

    created_jobs = create_jobspy_jobs_batch(jobs_to_create)
    result.new_jobs = len(created_jobs)
    logger.info("JobSpy: inserted %d new jobs into jobspy_jobs", len(created_jobs))

    # Convert to vacancies
    vacancies_to_create = [_jobspy_to_vacancy(job) for job in created_jobs]

    if vacancies_to_create:
        created_vacancies = create_vacancies_batch(vacancies_to_create)
        result.vacancies_created = len(created_vacancies)
        logger.info("JobSpy: created %d vacancies", len(created_vacancies))

    return result
