"""JobSpy scraping wrapper.

Wraps the python-jobspy library to search for jobs on LinkedIn,
Indeed, Glassdoor, and Google Jobs. Returns structured results
ready for database insertion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class JobSpySearchConfig:
    """Configuration for a single JobSpy search."""

    sites: List[str]
    search_term: str
    location: Optional[str] = None
    country: str = "USA"
    results_wanted: int = 20
    hours_old: int = 24
    is_remote: Optional[bool] = None
    job_type: Optional[str] = None
    proxies: Optional[List[str]] = None


@dataclass
class JobSpyRawResult:
    """Single job result from JobSpy scraper."""

    site: str
    job_url: str
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    date_posted: Optional[str] = None
    salary_min: Optional[Decimal] = None
    salary_max: Optional[Decimal] = None
    salary_currency: Optional[str] = None
    job_type: Optional[str] = None
    is_remote: Optional[bool] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)


def _safe_str(value: Any) -> Optional[str]:
    """Convert a value to string, handling NaN/None."""
    if value is None:
        return None
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    s = str(value)
    return s if s and s.lower() not in ("nan", "none", "nat") else None


def _safe_decimal(value: Any) -> Optional[Decimal]:
    """Convert a value to Decimal, handling NaN/None."""
    if value is None:
        return None
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
        return Decimal(str(value))
    except (TypeError, ValueError, ArithmeticError):
        return None


def _safe_bool(value: Any) -> Optional[bool]:
    """Convert a value to bool, handling NaN/None."""
    if value is None:
        return None
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return value
    return None


def _build_scrape_kwargs(config: JobSpySearchConfig) -> Dict[str, Any]:
    """Build keyword arguments for jobspy.scrape_jobs()."""
    kwargs: Dict[str, Any] = {
        "site_name": config.sites,
        "search_term": config.search_term,
        "results_wanted": config.results_wanted,
        "hours_old": config.hours_old,
        "country_indeed": config.country,
    }
    if config.location:
        kwargs["location"] = config.location
    if config.is_remote is not None:
        kwargs["is_remote"] = config.is_remote
    if config.job_type:
        kwargs["job_type"] = config.job_type
    if config.proxies:
        kwargs["proxies"] = config.proxies
    return kwargs


def _parse_df_row(row: Any, columns: List[str]) -> Optional[JobSpyRawResult]:
    """Parse a single DataFrame row into a JobSpyRawResult."""
    job_url = _safe_str(row.get("job_url"))
    if not job_url:
        return None

    site = _safe_str(row.get("site")) or "unknown"
    raw_data: Dict[str, Any] = {col: _safe_str(row.get(col)) for col in columns}

    return JobSpyRawResult(
        site=site,
        job_url=job_url,
        title=_safe_str(row.get("title")),
        company=_safe_str(row.get("company_name")) or _safe_str(row.get("company")),
        location=_safe_str(row.get("location")),
        description=_safe_str(row.get("description")),
        date_posted=_safe_str(row.get("date_posted")),
        salary_min=_safe_decimal(row.get("min_amount")),
        salary_max=_safe_decimal(row.get("max_amount")),
        salary_currency=_safe_str(row.get("currency")),
        job_type=_safe_str(row.get("job_type")),
        is_remote=_safe_bool(row.get("is_remote")),
        raw_data=raw_data,
    )


def scrape_jobspy(config: JobSpySearchConfig) -> List[JobSpyRawResult]:
    """Execute a JobSpy search and return structured results.

    Wraps jobspy.scrape_jobs(), converting the returned DataFrame
    into a list of JobSpyRawResult dataclasses.

    Args:
        config: Search configuration

    Returns:
        List of job results. Returns empty list on error.
    """
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.error("python-jobspy is not installed")
        return []

    try:
        kwargs = _build_scrape_kwargs(config)

        logger.info(
            "JobSpy search: sites=%s, term='%s', location=%s, results=%d",
            config.sites,
            config.search_term,
            config.location,
            config.results_wanted,
        )

        df = scrape_jobs(**kwargs)

        if df is None or df.empty:
            logger.info("JobSpy returned no results for '%s'", config.search_term)
            return []

        columns = list(df.columns)
        results: List[JobSpyRawResult] = []
        for _, row in df.iterrows():
            parsed = _parse_df_row(row, columns)
            if parsed:
                results.append(parsed)

        logger.info(
            "JobSpy returned %d results for '%s'",
            len(results),
            config.search_term,
        )
        return results

    except Exception:
        logger.exception("JobSpy scrape failed for '%s'", config.search_term)
        return []
