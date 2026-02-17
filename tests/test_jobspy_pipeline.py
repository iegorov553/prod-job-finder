"""Tests for JobSpy pipeline orchestration."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from job_finder.db.models import JobSpyJobDB
from job_finder.jobspy_pipeline import _jobspy_to_vacancy, run_jobspy_pipeline
from job_finder.jobspy_scraper import JobSpyRawResult


class TestJobspyToVacancy:
    """Tests for _jobspy_to_vacancy conversion."""

    def test_basic_conversion(self) -> None:
        """Should convert JobSpyJobDB to VacancyCreate with correct fields."""
        job = JobSpyJobDB(
            id=1,
            site="indeed",
            job_url="https://indeed.com/job/123",
            title="Product Manager",
            company="TechCorp",
            location="New York",
            description="A great PM role with product strategy responsibilities.",
            date_posted="2024-01-15",
            salary_min=Decimal("100000"),
            salary_max=Decimal("150000"),
            salary_currency="USD",
            job_type="fulltime",
            is_remote=False,
        )

        vacancy = _jobspy_to_vacancy(job)

        assert vacancy.source_type == "jobspy"
        assert vacancy.jobspy_job_id == 1
        assert vacancy.post_id is None
        assert vacancy.title == "Product Manager"
        assert vacancy.company == "TechCorp"
        assert vacancy.is_relevant is True
        assert vacancy.apply_link == "https://indeed.com/job/123"
        assert vacancy.remote_type == "unknown"
        assert vacancy.language == "en"
        assert vacancy.salary_min_usd == Decimal("100000")
        assert vacancy.salary_max_usd == Decimal("150000")
        assert vacancy.salary_raw == "USD 100000 - 150000"
        assert len(vacancy.links_json) == 1
        assert vacancy.links_json[0].type == "job_board_post"

    def test_remote_job(self) -> None:
        """Should set remote_type='remote' for remote jobs."""
        job = JobSpyJobDB(
            id=2,
            site="google",
            job_url="https://google.com/job/456",
            is_remote=True,
        )

        vacancy = _jobspy_to_vacancy(job)

        assert vacancy.remote_type == "remote"

    def test_truncates_description(self) -> None:
        """Should truncate description to 500 chars for raw_snippet."""
        long_desc = "A" * 1000
        job = JobSpyJobDB(
            id=3,
            site="indeed",
            job_url="https://indeed.com/job/789",
            description=long_desc,
        )

        vacancy = _jobspy_to_vacancy(job)

        assert vacancy.raw_snippet is not None
        assert len(vacancy.raw_snippet) == 500

    def test_no_salary(self) -> None:
        """Should handle missing salary fields."""
        job = JobSpyJobDB(
            id=4,
            site="glassdoor",
            job_url="https://glassdoor.com/job/101",
        )

        vacancy = _jobspy_to_vacancy(job)

        assert vacancy.salary_min_usd is None
        assert vacancy.salary_max_usd is None
        assert vacancy.salary_raw is None

    def test_relevance_reason_includes_site(self) -> None:
        """Should include site name in relevance_reason."""
        job = JobSpyJobDB(
            id=5,
            site="linkedin",
            job_url="https://linkedin.com/job/202",
        )

        vacancy = _jobspy_to_vacancy(job)

        assert "linkedin" in (vacancy.relevance_reason or "")


class TestRunJobspyPipeline:
    """Tests for run_jobspy_pipeline function."""

    def _make_settings_manager(
        self,
        enabled: bool = True,
        sites: list[str] | None = None,
        search_terms: list[str] | None = None,
    ) -> MagicMock:
        """Create a mock SettingsManager with JobSpy config."""
        mgr = MagicMock()
        mgr.get_jobspy_enabled.return_value = enabled

        if enabled:
            mgr.get_jobspy_config.return_value = {
                "sites": sites or ["indeed", "google"],
                "location": None,
                "country": "USA",
                "results_wanted": 20,
                "hours_old": 24,
                "is_remote": None,
                "job_type": None,
            }
        else:
            mgr.get_jobspy_config.return_value = None

        mgr.get_jobspy_search_terms.return_value = search_terms or ["Product Manager"]
        return mgr

    @patch("job_finder.jobspy_pipeline.create_vacancies_batch")
    @patch("job_finder.jobspy_pipeline.create_jobspy_jobs_batch")
    @patch("job_finder.jobspy_pipeline.get_existing_job_urls")
    @patch("job_finder.jobspy_pipeline.scrape_jobspy")
    def test_full_pipeline(
        self,
        mock_scrape: MagicMock,
        mock_existing: MagicMock,
        mock_create_jobs: MagicMock,
        mock_create_vacancies: MagicMock,
    ) -> None:
        """Should scrape, dedup, create jobs, and create vacancies."""
        # scrape returns 2 results
        mock_scrape.return_value = [
            JobSpyRawResult(
                site="indeed",
                job_url="https://indeed.com/1",
                title="PM 1",
                company="Corp A",
            ),
            JobSpyRawResult(
                site="google",
                job_url="https://google.com/2",
                title="PM 2",
                company="Corp B",
            ),
        ]

        # No existing URLs
        mock_existing.return_value = set()

        # Jobs created successfully
        mock_create_jobs.return_value = [
            JobSpyJobDB(
                id=1,
                site="indeed",
                job_url="https://indeed.com/1",
                title="PM 1",
                company="Corp A",
            ),
            JobSpyJobDB(
                id=2,
                site="google",
                job_url="https://google.com/2",
                title="PM 2",
                company="Corp B",
            ),
        ]

        # Vacancies created
        mock_create_vacancies.return_value = [MagicMock(), MagicMock()]

        mgr = self._make_settings_manager()
        result = run_jobspy_pipeline(mgr)

        assert result.total_scraped == 2
        assert result.new_jobs == 2
        assert result.duplicates_skipped == 0
        assert result.vacancies_created == 2

    @patch("job_finder.jobspy_pipeline.scrape_jobspy")
    def test_disabled_returns_empty(self, mock_scrape: MagicMock) -> None:
        """Should return empty result when JobSpy is disabled."""
        mgr = self._make_settings_manager(enabled=False)
        result = run_jobspy_pipeline(mgr)

        assert result.total_scraped == 0
        assert result.new_jobs == 0
        mock_scrape.assert_not_called()

    @patch("job_finder.jobspy_pipeline.get_existing_job_urls")
    @patch("job_finder.jobspy_pipeline.scrape_jobspy")
    def test_deduplication(
        self,
        mock_scrape: MagicMock,
        mock_existing: MagicMock,
    ) -> None:
        """Should skip jobs that already exist in DB."""
        mock_scrape.return_value = [
            JobSpyRawResult(
                site="indeed",
                job_url="https://indeed.com/existing",
                title="Old PM",
            ),
            JobSpyRawResult(
                site="google",
                job_url="https://google.com/new",
                title="New PM",
            ),
        ]

        mock_existing.return_value = {"https://indeed.com/existing"}

        mgr = self._make_settings_manager()

        with patch("job_finder.jobspy_pipeline.create_jobspy_jobs_batch") as mock_create:
            mock_create.return_value = []
            with patch("job_finder.jobspy_pipeline.create_vacancies_batch"):
                result = run_jobspy_pipeline(mgr)

        assert result.total_scraped == 2
        assert result.duplicates_skipped == 1

        # Only 1 job should be passed to create
        create_args = mock_create.call_args[0][0]
        assert len(create_args) == 1
        assert create_args[0].job_url == "https://google.com/new"

    @patch("job_finder.jobspy_pipeline.scrape_jobspy")
    def test_no_results(self, mock_scrape: MagicMock) -> None:
        """Should handle case when scraper returns no results."""
        mock_scrape.return_value = []

        mgr = self._make_settings_manager()
        result = run_jobspy_pipeline(mgr)

        assert result.total_scraped == 0
        assert result.new_jobs == 0

    @patch("job_finder.jobspy_pipeline.scrape_jobspy")
    def test_dedup_within_batch(self, mock_scrape: MagicMock) -> None:
        """Should deduplicate same URLs within a single batch."""
        # Same URL appears twice (e.g. from two search terms)
        mock_scrape.side_effect = [
            [
                JobSpyRawResult(
                    site="indeed",
                    job_url="https://indeed.com/same",
                    title="PM",
                ),
            ],
            [
                JobSpyRawResult(
                    site="indeed",
                    job_url="https://indeed.com/same",
                    title="PM duplicate",
                ),
            ],
        ]

        mgr = self._make_settings_manager(search_terms=["Product Manager", "PM"])

        with patch("job_finder.jobspy_pipeline.get_existing_job_urls", return_value=set()):
            with patch("job_finder.jobspy_pipeline.create_jobspy_jobs_batch") as mock_create:
                mock_create.return_value = []
                with patch("job_finder.jobspy_pipeline.create_vacancies_batch"):
                    result = run_jobspy_pipeline(mgr)

        assert result.total_scraped == 2
        # Only 1 unique URL should be passed to create
        create_args = mock_create.call_args[0][0]
        assert len(create_args) == 1
