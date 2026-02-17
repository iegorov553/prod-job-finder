"""Tests for jobspy_jobs CRUD operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from job_finder.db.models import JobSpyJobCreate


class TestCreateJobSpyJobsBatch:
    """Tests for create_jobspy_jobs_batch function."""

    def test_create_batch_success(self) -> None:
        """Should create multiple jobspy_job records."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "site": "indeed",
                "job_url": "https://indeed.com/job/123",
                "title": "Product Manager",
                "company": "TechCorp",
                "location": "New York, NY",
                "description": "Job description here...",
                "date_posted": "2024-01-15",
                "salary_min": "100000",
                "salary_max": "150000",
                "salary_currency": "USD",
                "job_type": "fulltime",
                "is_remote": False,
                "search_term": "Product Manager",
                "raw_data": {"site": "indeed"},
                "created_at": "2024-01-15T10:00:00Z",
            },
            {
                "id": 2,
                "site": "google",
                "job_url": "https://google.com/job/456",
                "title": "Senior PM",
                "company": "BigCo",
                "location": "Remote",
                "description": None,
                "date_posted": None,
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "job_type": None,
                "is_remote": True,
                "search_term": "Product Manager",
                "raw_data": {},
                "created_at": "2024-01-15T10:00:00Z",
            },
        ]
        (mock_client.table.return_value.upsert.return_value.execute.return_value) = mock_response

        with patch(
            "job_finder.db.jobspy_jobs.get_supabase_client",
            return_value=mock_client,
        ):
            from job_finder.db.jobspy_jobs import create_jobspy_jobs_batch

            jobs = [
                JobSpyJobCreate(
                    site="indeed",
                    job_url="https://indeed.com/job/123",
                    title="Product Manager",
                    company="TechCorp",
                ),
                JobSpyJobCreate(
                    site="google",
                    job_url="https://google.com/job/456",
                    title="Senior PM",
                ),
            ]
            result = create_jobspy_jobs_batch(jobs)

        assert len(result) == 2
        assert result[0].site == "indeed"
        assert result[1].is_remote is True

    def test_create_batch_empty(self) -> None:
        """Should return empty list for empty input."""
        with patch("job_finder.db.jobspy_jobs.get_supabase_client"):
            from job_finder.db.jobspy_jobs import create_jobspy_jobs_batch

            result = create_jobspy_jobs_batch([])

        assert result == []

    def test_upsert_uses_job_url_conflict(self) -> None:
        """Should use job_url as dedup key with ignore_duplicates."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        (mock_client.table.return_value.upsert.return_value.execute.return_value) = mock_response

        with patch(
            "job_finder.db.jobspy_jobs.get_supabase_client",
            return_value=mock_client,
        ):
            from job_finder.db.jobspy_jobs import create_jobspy_jobs_batch

            create_jobspy_jobs_batch(
                [JobSpyJobCreate(site="indeed", job_url="https://example.com/1")]
            )

        mock_client.table.return_value.upsert.assert_called_once()
        call_kwargs = mock_client.table.return_value.upsert.call_args
        assert call_kwargs.kwargs["on_conflict"] == "job_url"
        assert call_kwargs.kwargs["ignore_duplicates"] is True


class TestGetExistingJobUrls:
    """Tests for get_existing_job_urls function."""

    def test_returns_existing_urls(self) -> None:
        """Should return set of URLs that exist in DB."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {"job_url": "https://indeed.com/1"},
            {"job_url": "https://indeed.com/2"},
        ]
        (
            mock_client.table.return_value.select.return_value.in_.return_value.execute.return_value
        ) = mock_response

        with patch(
            "job_finder.db.jobspy_jobs.get_supabase_client",
            return_value=mock_client,
        ):
            from job_finder.db.jobspy_jobs import get_existing_job_urls

            result = get_existing_job_urls(
                ["https://indeed.com/1", "https://indeed.com/2", "https://indeed.com/3"]
            )

        assert result == {"https://indeed.com/1", "https://indeed.com/2"}

    def test_empty_input_returns_empty_set(self) -> None:
        """Should return empty set for empty input."""
        with patch("job_finder.db.jobspy_jobs.get_supabase_client"):
            from job_finder.db.jobspy_jobs import get_existing_job_urls

            result = get_existing_job_urls([])

        assert result == set()


class TestGetJobSpyJobById:
    """Tests for get_jobspy_job_by_id function."""

    def test_returns_job_when_found(self) -> None:
        """Should return JobSpyJobDB when job exists."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 42,
                "site": "linkedin",
                "job_url": "https://linkedin.com/jobs/42",
                "title": "Product Manager",
                "company": "ACME",
                "location": "San Francisco",
                "description": "Great job",
                "date_posted": "2024-01-15",
                "salary_min": None,
                "salary_max": None,
                "salary_currency": None,
                "job_type": "fulltime",
                "is_remote": False,
                "search_term": "PM",
                "raw_data": None,
                "created_at": None,
            }
        ]
        (
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value
        ) = mock_response

        with patch(
            "job_finder.db.jobspy_jobs.get_supabase_client",
            return_value=mock_client,
        ):
            from job_finder.db.jobspy_jobs import get_jobspy_job_by_id

            result = get_jobspy_job_by_id(42)

        assert result is not None
        assert result.id == 42
        assert result.site == "linkedin"
        assert result.title == "Product Manager"

    def test_returns_none_when_not_found(self) -> None:
        """Should return None when job doesn't exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        (
            mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value
        ) = mock_response

        with patch(
            "job_finder.db.jobspy_jobs.get_supabase_client",
            return_value=mock_client,
        ):
            from job_finder.db.jobspy_jobs import get_jobspy_job_by_id

            result = get_jobspy_job_by_id(999)

        assert result is None
