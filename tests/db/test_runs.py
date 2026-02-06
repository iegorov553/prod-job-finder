"""Tests for runs CRUD operations."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from job_finder.db.models import RunUpdate


class TestCreateRun:
    def test_create_run_success(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "status": "running",
                "digest_md": None,
                "error": None,
                "started_at": "2026-02-04T10:00:00Z",
                "finished_at": None,
                "created_at": "2026-02-04T10:00:00Z",
            }
        ]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.runs.get_supabase_client", return_value=mock_client):
            from job_finder.db.runs import create_run

            run = create_run()

        assert run.id == 1
        assert run.status == "running"
        mock_client.table.return_value.insert.assert_called_once()


class TestGetLatestRun:
    def test_get_latest_run_success(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 2,
                "status": "success",
                "digest_md": "Digest",
                "error": None,
                "started_at": "2026-02-04T11:00:00Z",
                "finished_at": "2026-02-04T11:05:00Z",
                "created_at": "2026-02-04T11:00:00Z",
            }
        ]
        select_query = (
            mock_client.table.return_value.select.return_value.order.return_value.limit.return_value
        )
        select_query.execute.return_value = mock_response

        with patch("job_finder.db.runs.get_supabase_client", return_value=mock_client):
            from job_finder.db.runs import get_latest_run

            run = get_latest_run()

        assert run is not None
        assert run.id == 2
        assert run.status == "success"

    def test_get_latest_run_empty(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        select_query = (
            mock_client.table.return_value.select.return_value.order.return_value.limit.return_value
        )
        select_query.execute.return_value = mock_response

        with patch("job_finder.db.runs.get_supabase_client", return_value=mock_client):
            from job_finder.db.runs import get_latest_run

            run = get_latest_run()

        assert run is None


class TestGetRunningRun:
    def test_get_running_run_success(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 3,
                "status": "running",
                "digest_md": None,
                "error": None,
                "started_at": "2026-02-04T12:00:00Z",
                "finished_at": None,
                "created_at": "2026-02-04T12:00:00Z",
            }
        ]
        table = mock_client.table.return_value
        select_query = table.select.return_value.eq.return_value.order.return_value
        select_query = select_query.limit.return_value
        select_query.execute.return_value = mock_response

        with patch("job_finder.db.runs.get_supabase_client", return_value=mock_client):
            from job_finder.db.runs import get_running_run

            run = get_running_run()

        assert run is not None
        assert run.status == "running"


class TestUpdateRun:
    def test_update_run_success(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 4,
                "status": "success",
                "digest_md": "Digest",
                "error": None,
                "started_at": "2026-02-04T13:00:00Z",
                "finished_at": "2026-02-04T13:05:00Z",
                "created_at": "2026-02-04T13:00:00Z",
            }
        ]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.runs.get_supabase_client", return_value=mock_client):
            from job_finder.db.runs import update_run

            update = RunUpdate(status="success", digest_md="Digest")
            run = update_run(4, update)

        assert run is not None
        assert run.status == "success"
        mock_client.table.return_value.update.assert_called_once()


class TestMarkRunningFailed:
    def test_mark_running_failed_updates_rows(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 5,
                "status": "failed",
                "digest_md": None,
                "error": "aborted",
                "started_at": "2026-02-04T14:00:00Z",
                "finished_at": "2026-02-04T14:01:00Z",
                "created_at": "2026-02-04T14:00:00Z",
            }
        ]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.runs.get_supabase_client", return_value=mock_client):
            from job_finder.db.runs import mark_running_failed

            updated = mark_running_failed("aborted")

        assert updated == 1
        update_payload = mock_client.table.return_value.update.call_args[0][0]
        assert update_payload["status"] == "failed"
        assert update_payload["error"] == "aborted"
        assert isinstance(update_payload["finished_at"], str)
        parsed_finished_at = datetime.fromisoformat(update_payload["finished_at"])
        assert parsed_finished_at.tzinfo is not None
        mock_client.table.return_value.update.assert_called_once()
        mock_client.table.return_value.update.return_value.eq.assert_called_once_with(
            "status", "running"
        )
