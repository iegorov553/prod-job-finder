"""CRUD operations for jobspy_jobs table.

This module provides functions to manage job records scraped
by JobSpy from LinkedIn, Indeed, Glassdoor, and Google Jobs.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Set, cast

from job_finder.db.client import get_supabase_client
from job_finder.db.models import JobSpyJobCreate, JobSpyJobDB

logger = logging.getLogger(__name__)

TABLE_NAME = "jobspy_jobs"


def create_jobspy_jobs_batch(jobs: List[JobSpyJobCreate]) -> List[JobSpyJobDB]:
    """Create multiple jobspy_job records in a single batch operation.

    Uses upsert with ON CONFLICT (job_url) DO NOTHING to skip duplicates.

    Args:
        jobs: List of job records to create

    Returns:
        List of created JobSpyJobDB objects (excludes skipped duplicates)
    """
    if not jobs:
        return []

    client = get_supabase_client()
    payloads = [job.model_dump(mode="json") for job in jobs]

    response = (
        client.table(TABLE_NAME)
        .upsert(payloads, on_conflict="job_url", ignore_duplicates=True)
        .execute()
    )

    return [JobSpyJobDB.model_validate(row) for row in response.data]


def get_existing_job_urls(urls: List[str]) -> Set[str]:
    """Check which job URLs already exist in the database.

    Used for pre-filtering before insert to avoid unnecessary processing.

    Args:
        urls: List of job URLs to check

    Returns:
        Set of URLs that already exist in the database
    """
    if not urls:
        return set()

    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("job_url").in_("job_url", urls).execute()

    return {row["job_url"] for row in response.data}


def get_jobspy_job_by_id(job_id: int) -> Optional[JobSpyJobDB]:
    """Get a jobspy_job by its database ID.

    Args:
        job_id: Database ID of the job record

    Returns:
        JobSpyJobDB if found, None otherwise
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").eq("id", job_id).execute()

    if not response.data:
        return None

    return cast(JobSpyJobDB, JobSpyJobDB.model_validate(response.data[0]))
