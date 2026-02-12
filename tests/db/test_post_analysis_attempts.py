"""Tests for post_analysis_attempts CRUD operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestCreatePostAnalysisAttempts:
    def test_create_attempts_batch(self) -> None:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [{"id": 1}, {"id": 2}]
        mock_insert = mock_client.table.return_value.insert
        mock_insert.return_value.execute.return_value = mock_response

        with patch(
            "job_finder.db.post_analysis_attempts.get_supabase_client",
            return_value=mock_client,
        ):
            from job_finder.db.post_analysis_attempts import create_post_analysis_attempts

            count = create_post_analysis_attempts(
                [
                    {
                        "run_id": 7,
                        "post_id": 100,
                        "batch_id": "b-1",
                        "attempt_no": 1,
                        "model_name": "gpt-5-nano",
                        "timeout_sec": 90,
                        "http_status": 500,
                        "error_code": "http_5xx",
                        "error_message": "HTTP 500",
                        "response_excerpt": "",
                    },
                    {
                        "run_id": 7,
                        "post_id": 101,
                        "batch_id": "b-1",
                        "attempt_no": 1,
                        "model_name": "gpt-5-nano",
                        "timeout_sec": 90,
                        "http_status": 500,
                        "error_code": "http_5xx",
                        "error_message": "HTTP 500",
                        "response_excerpt": "",
                    },
                ]
            )

        assert count == 2
        assert mock_insert.call_count == 1
        payload = mock_insert.call_args[0][0]
        assert len(payload) == 2
        assert payload[0]["error_code"] == "http_5xx"

    def test_create_attempts_batch_empty(self) -> None:
        with patch("job_finder.db.post_analysis_attempts.get_supabase_client"):
            from job_finder.db.post_analysis_attempts import create_post_analysis_attempts

            count = create_post_analysis_attempts([])

        assert count == 0
