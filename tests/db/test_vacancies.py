"""Tests for vacancies CRUD operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from job_finder.db.models import (
    VacancyCreate,
    VacancyEnrichmentUpdate,
    VacancyLink,
    VacancyUpdate,
)


class TestCreateVacancy:
    """Tests for create_vacancy function."""

    def test_create_vacancy_success(self) -> None:
        """Should create a new vacancy and return VacancyDB."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "post_id": 10,
                "title": "Product Manager",
                "company": "TechCorp",
                "industry": "Fintech",
                "level": "senior",
                "location": "Barcelona",
                "remote_type": "hybrid",
                "salary_min_usd": "100000.00",
                "salary_max_usd": "150000.00",
                "salary_raw": "$100k-150k",
                "language": "en",
                "is_relevant": True,
                "relevance_reason": "Matches criteria",
                "status": "new",
                "apply_link": None,
                "links_json": [{"url": "https://example.com/apply", "type": "apply_direct"}],
                "notes": None,
                "cover_letter": None,
                "raw_snippet": "Job text...",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
            }
        ]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import create_vacancy

            data = VacancyCreate(
                post_id=10,
                title="Product Manager",
                company="TechCorp",
                industry="Fintech",
                level="senior",
                is_relevant=True,
                relevance_reason="Matches criteria",
                links_json=[VacancyLink(url="https://example.com/apply", type="apply_direct")],
            )
            result = create_vacancy(data)

        assert result.id == 1
        assert result.title == "Product Manager"
        assert result.is_relevant is True
        assert result.links_json[0].type == "apply_direct"


class TestCreateVacanciesBatch:
    """Tests for create_vacancies_batch function."""

    def test_create_batch_success(self) -> None:
        """Should create multiple vacancies."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "post_id": 10,
                "title": "PM 1",
                "company": None,
                "industry": None,
                "level": None,
                "location": None,
                "remote_type": "unknown",
                "salary_min_usd": None,
                "salary_max_usd": None,
                "salary_raw": None,
                "language": None,
                "is_relevant": True,
                "relevance_reason": None,
                "status": "new",
                "apply_link": None,
                "links_json": [],
                "notes": None,
                "cover_letter": None,
                "raw_snippet": None,
                "created_at": None,
                "updated_at": None,
            },
            {
                "id": 2,
                "post_id": 10,
                "title": "PM 2",
                "company": None,
                "industry": None,
                "level": None,
                "location": None,
                "remote_type": "unknown",
                "salary_min_usd": None,
                "salary_max_usd": None,
                "salary_raw": None,
                "language": None,
                "is_relevant": False,
                "relevance_reason": None,
                "status": "new",
                "apply_link": None,
                "links_json": [],
                "notes": None,
                "cover_letter": None,
                "raw_snippet": None,
                "created_at": None,
                "updated_at": None,
            },
        ]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import create_vacancies_batch

            vacancies = [
                VacancyCreate(post_id=10, title="PM 1", is_relevant=True),
                VacancyCreate(post_id=10, title="PM 2", is_relevant=False),
            ]
            result = create_vacancies_batch(vacancies)

        assert len(result) == 2
        assert result[0].is_relevant is True
        assert result[1].is_relevant is False

    def test_create_batch_empty(self) -> None:
        """Should return empty list for empty input."""
        with patch("job_finder.db.vacancies.get_supabase_client"):
            from job_finder.db.vacancies import create_vacancies_batch

            result = create_vacancies_batch([])

        assert result == []


class TestGetRelevantVacancies:
    """Tests for get_relevant_vacancies function."""

    def test_get_relevant_only(self) -> None:
        """Should return only relevant vacancies."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "post_id": 10,
                "title": "Relevant PM",
                "company": "Corp",
                "industry": None,
                "level": "senior",
                "location": "Remote",
                "remote_type": "remote",
                "salary_min_usd": "100000",
                "salary_max_usd": "120000",
                "salary_raw": None,
                "language": "en",
                "is_relevant": True,
                "relevance_reason": "Good match",
                "status": "new",
                "apply_link": None,
                "links_json": [],
                "notes": None,
                "cover_letter": None,
                "raw_snippet": "Job...",
                "created_at": None,
                "updated_at": None,
            }
        ]
        (
            mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value
        ) = mock_response

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import get_relevant_vacancies

            result = get_relevant_vacancies(limit=50)

        assert len(result) == 1
        assert result[0].is_relevant is True


class TestGetVacanciesByPostId:
    """Tests for get_vacancies_by_post_id function."""

    def test_get_by_post_id(self) -> None:
        """Should return all vacancies for a post."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "post_id": 10,
                "title": "PM",
                "company": None,
                "industry": None,
                "level": None,
                "location": None,
                "remote_type": "unknown",
                "salary_min_usd": None,
                "salary_max_usd": None,
                "salary_raw": None,
                "language": None,
                "is_relevant": True,
                "relevance_reason": None,
                "status": "new",
                "apply_link": None,
                "links_json": [],
                "notes": None,
                "cover_letter": None,
                "raw_snippet": None,
                "created_at": None,
                "updated_at": None,
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import get_vacancies_by_post_id

            result = get_vacancies_by_post_id(10)

        assert len(result) == 1
        assert result[0].post_id == 10


class TestUpdateVacancy:
    """Tests for update_vacancy function."""

    def test_update_vacancy_status(self) -> None:
        """Should update vacancy fields."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "post_id": 10,
                "title": "PM",
                "company": None,
                "industry": None,
                "level": None,
                "location": None,
                "remote_type": "unknown",
                "salary_min_usd": None,
                "salary_max_usd": None,
                "salary_raw": None,
                "language": None,
                "is_relevant": True,
                "relevance_reason": None,
                "status": "applied",
                "apply_link": "https://apply.com",
                "links_json": [],
                "notes": "Applied via email",
                "cover_letter": None,
                "raw_snippet": None,
                "created_at": None,
                "updated_at": None,
            }
        ]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import update_vacancy

            update = VacancyUpdate(
                status="applied",
                apply_link="https://apply.com",
                notes="Applied via email",
            )
            result = update_vacancy(1, update)

        assert result is not None
        assert result.status == "applied"
        assert result.notes == "Applied via email"


class TestGetVacanciesByStatus:
    """Tests for get_vacancies_by_status function."""

    def test_filter_by_status(self) -> None:
        """Should return vacancies with specified status."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "post_id": 10,
                "title": "Applied PM",
                "company": None,
                "industry": None,
                "level": None,
                "location": None,
                "remote_type": "unknown",
                "salary_min_usd": None,
                "salary_max_usd": None,
                "salary_raw": None,
                "language": None,
                "is_relevant": True,
                "relevance_reason": None,
                "status": "applied",
                "apply_link": None,
                "links_json": [],
                "notes": None,
                "cover_letter": None,
                "raw_snippet": None,
                "created_at": None,
                "updated_at": None,
            }
        ]
        (
            mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value
        ) = mock_response

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import get_vacancies_by_status

            result = get_vacancies_by_status("applied")

        assert len(result) == 1
        assert result[0].status == "applied"


class TestGetNewRelevantVacancies:
    """Tests for get_new_relevant_vacancies function."""

    def test_get_today_relevant_vacancies(self) -> None:
        """Should return relevant vacancies created today."""
        from datetime import datetime, timezone

        mock_client = MagicMock()
        mock_response = MagicMock()
        now = datetime.now(timezone.utc)
        mock_response.data = [
            {
                "id": 1,
                "post_id": 10,
                "title": "Today PM",
                "company": "TechCorp",
                "industry": None,
                "level": "senior",
                "location": "Remote",
                "remote_type": "remote",
                "salary_min_usd": None,
                "salary_max_usd": None,
                "salary_raw": None,
                "language": "en",
                "is_relevant": True,
                "relevance_reason": "Great match",
                "status": "new",
                "apply_link": None,
                "links_json": [],
                "notes": None,
                "cover_letter": None,
                "raw_snippet": "Job...",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        ]
        (
            mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value
        ) = mock_response

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import get_new_relevant_vacancies

            result = get_new_relevant_vacancies(limit=50)

        assert len(result) == 1
        assert result[0].is_relevant is True
        assert result[0].title == "Today PM"

    def test_filters_by_today_date(self) -> None:
        """Should filter vacancies created >= start of today."""
        from datetime import datetime, timezone

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []

        (
            mock_client.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value
        ) = mock_response

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import get_new_relevant_vacancies

            get_new_relevant_vacancies(limit=100)

        # Verify gte was called with created_at and today's date
        gte_call = mock_client.table.return_value.select.return_value.eq.return_value.gte
        gte_call.assert_called_once()
        call_args = gte_call.call_args[0]

        assert call_args[0] == "created_at"
        # Check that the timestamp is today's start (allow small time delta)
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        assert call_args[1].startswith(today_start.date().isoformat())


class TestUpdateVacanciesEnrichment:
    """Tests for update_vacancies_enrichment function."""

    def test_update_vacancies_enrichment_batch(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}]
        (
            mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value
        ) = mock_response

        with patch("job_finder.db.vacancies.get_supabase_client", return_value=mock_client):
            from job_finder.db.vacancies import update_vacancies_enrichment

            updates = [
                VacancyEnrichmentUpdate(
                    id=1,
                    enrichment_status="success",
                    enrichment_attempts=1,
                    vacancy_text_full="Vacancy text",
                    vacancy_text_source_url="https://jobs.example/1",
                ),
                VacancyEnrichmentUpdate(
                    id=2,
                    enrichment_status="failed",
                    enrichment_attempts=2,
                    enrichment_error="No useful text found",
                ),
            ]

            updated_count = update_vacancies_enrichment(updates)

        assert updated_count == 2
        assert mock_client.table.return_value.update.call_count == 2

    def test_update_vacancies_enrichment_empty(self) -> None:
        with patch("job_finder.db.vacancies.get_supabase_client"):
            from job_finder.db.vacancies import update_vacancies_enrichment

            result = update_vacancies_enrichment([])

        assert result == 0
