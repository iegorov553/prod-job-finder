"""CRUD operations for vacancies table.

This module provides functions to manage vacancies in Supabase.
Vacancies are extracted from posts by LLM analysis.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, cast

from job_finder.db.client import get_supabase_client
from job_finder.db.models import VacancyCreate, VacancyDB, VacancyEnrichmentUpdate, VacancyUpdate

logger = logging.getLogger(__name__)

TABLE_NAME = "vacancies"


def create_vacancy(data: VacancyCreate) -> VacancyDB:
    """Create a single vacancy in the database.

    Args:
        data: Vacancy data to create

    Returns:
        Created VacancyDB with generated id
    """
    client = get_supabase_client()
    payload = data.model_dump(mode="json")

    response = client.table(TABLE_NAME).insert(payload).execute()

    return cast(VacancyDB, VacancyDB.model_validate(response.data[0]))


def create_vacancies_batch(vacancies: List[VacancyCreate]) -> List[VacancyDB]:
    """Create multiple vacancies in a single batch operation.

    Args:
        vacancies: List of vacancies to create

    Returns:
        List of created VacancyDB objects
    """
    if not vacancies:
        return []

    client = get_supabase_client()
    payloads = [v.model_dump(mode="json") for v in vacancies]

    response = client.table(TABLE_NAME).insert(payloads).execute()

    return [VacancyDB.model_validate(row) for row in response.data]


def update_vacancies_enrichment(updates: List[VacancyEnrichmentUpdate]) -> int:
    """Update enrichment fields for multiple vacancies."""
    if not updates:
        return 0

    client = get_supabase_client()
    updated = 0

    for item in updates:
        payload = item.model_dump(mode="json", exclude_none=True)
        vacancy_id = payload.pop("id")
        response = client.table(TABLE_NAME).update(payload).eq("id", vacancy_id).execute()
        if response.data:
            updated += 1

    return updated


def get_vacancy_by_id(vacancy_id: int) -> Optional[VacancyDB]:
    """Get a vacancy by its database ID.

    Args:
        vacancy_id: Database ID of the vacancy

    Returns:
        VacancyDB if found, None otherwise
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").eq("id", vacancy_id).execute()

    if not response.data:
        return None

    return cast(VacancyDB, VacancyDB.model_validate(response.data[0]))


def get_vacancies_by_post_id(post_id: int) -> List[VacancyDB]:
    """Get all vacancies for a specific post.

    Args:
        post_id: Database ID of the post

    Returns:
        List of VacancyDB objects for the post
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").eq("post_id", post_id).execute()

    return [VacancyDB.model_validate(row) for row in response.data]


def get_relevant_vacancies(limit: int = 100) -> List[VacancyDB]:
    """Get vacancies marked as relevant.

    Args:
        limit: Maximum number of vacancies to return

    Returns:
        List of relevant VacancyDB objects
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").eq("is_relevant", True).limit(limit).execute()

    return [VacancyDB.model_validate(row) for row in response.data]


def get_vacancies_by_status(status: str, limit: int = 100) -> List[VacancyDB]:
    """Get vacancies by their application status.

    Args:
        status: Status to filter by (new, saved, applied, etc.)
        limit: Maximum number of vacancies to return

    Returns:
        List of VacancyDB objects with the specified status
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).select("*").eq("status", status).limit(limit).execute()

    return [VacancyDB.model_validate(row) for row in response.data]


def get_new_relevant_vacancies(limit: int = 100) -> List[VacancyDB]:
    """Get relevant vacancies created today for digest.

    Filters by is_relevant=True and created_at >= start of today (UTC).

    Args:
        limit: Maximum number of vacancies to return

    Returns:
        List of relevant VacancyDB objects created today
    """
    from datetime import datetime, timezone

    client = get_supabase_client()

    # Start of today in UTC
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_start_iso = today_start.isoformat()

    response = (
        client.table(TABLE_NAME)
        .select("*")
        .eq("is_relevant", True)
        .gte("created_at", today_start_iso)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return [VacancyDB.model_validate(row) for row in response.data]


def update_vacancy(vacancy_id: int, update: VacancyUpdate) -> Optional[VacancyDB]:
    """Update vacancy fields.

    Args:
        vacancy_id: Database ID of the vacancy
        update: Fields to update

    Returns:
        Updated VacancyDB if found, None otherwise
    """
    client = get_supabase_client()
    payload = update.model_dump(mode="json", exclude_none=True)

    if not payload:
        return get_vacancy_by_id(vacancy_id)

    response = client.table(TABLE_NAME).update(payload).eq("id", vacancy_id).execute()

    if not response.data:
        return None

    return cast(VacancyDB, VacancyDB.model_validate(response.data[0]))


def delete_vacancies_by_post_id(post_id: int) -> int:
    """Delete all vacancies for a specific post.

    Useful when re-analyzing a post.

    Args:
        post_id: Database ID of the post

    Returns:
        Number of deleted vacancies
    """
    client = get_supabase_client()
    response = client.table(TABLE_NAME).delete().eq("post_id", post_id).execute()

    return len(response.data)


def count_relevant_vacancies() -> int:
    """Count total relevant vacancies.

    Returns:
        Number of relevant vacancies
    """
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME)
        .select("id", count=cast(Any, "exact"))
        .eq("is_relevant", True)
        .execute()
    )

    return response.count or 0
