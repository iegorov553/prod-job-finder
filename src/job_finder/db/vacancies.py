"""CRUD operations for vacancies table.

This module provides functions to manage vacancies in Supabase.
Vacancies are extracted from posts by LLM analysis.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from job_finder.db.client import get_supabase_client
from job_finder.db.models import VacancyCreate, VacancyDB, VacancyUpdate

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

    return VacancyDB.model_validate(response.data[0])


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

    return VacancyDB.model_validate(response.data[0])


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
    """Get new vacancies that are relevant.

    Combines is_relevant=True and status='new' filters.

    Args:
        limit: Maximum number of vacancies to return

    Returns:
        List of new relevant VacancyDB objects
    """
    client = get_supabase_client()
    response = (
        client.table(TABLE_NAME)
        .select("*")
        .eq("is_relevant", True)
        .eq("status", "new")
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

    return VacancyDB.model_validate(response.data[0])


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
        client.table(TABLE_NAME).select("id", count="exact").eq("is_relevant", True).execute()
    )

    return response.count or 0
