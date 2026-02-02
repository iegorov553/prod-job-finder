"""Tests for posts CRUD operations."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from job_finder.db.models import PostCreate, PostUpdate


class TestCreatePost:
    """Tests for create_post function."""

    def test_create_post_success(self) -> None:
        """Should create a new post and return PostDB."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "telegram_id": 12345,
                "channel": "@test_channel",
                "telegram_date": "2024-01-15T10:00:00Z",
                "text_full": "Job post text",
                "source_link": "https://t.me/test_channel/12345",
                "links": [],
                "analyzed_at": None,
                "analysis_status": "pending",
                "vacancies_count": 0,
                "created_at": "2024-01-15T10:00:00Z",
            }
        ]
        mock_client.table.return_value.insert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.posts.get_supabase_client", return_value=mock_client):
            from job_finder.db.posts import create_post

            data = PostCreate(
                telegram_id=12345,
                channel="@test_channel",
                telegram_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                text_full="Job post text",
                source_link="https://t.me/test_channel/12345",
            )
            result = create_post(data)

        assert result.id == 1
        assert result.telegram_id == 12345
        assert result.analysis_status == "pending"


class TestCreatePostsBatch:
    """Tests for create_posts_batch function."""

    def test_create_batch_success(self) -> None:
        """Should create multiple posts and return list of PostDB."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "telegram_id": 100,
                "channel": "@ch",
                "telegram_date": "2024-01-15T10:00:00Z",
                "text_full": "Post 1",
                "source_link": None,
                "links": [],
                "analyzed_at": None,
                "analysis_status": "pending",
                "vacancies_count": 0,
                "created_at": None,
            },
            {
                "id": 2,
                "telegram_id": 101,
                "channel": "@ch",
                "telegram_date": "2024-01-15T10:00:00Z",
                "text_full": "Post 2",
                "source_link": None,
                "links": [],
                "analyzed_at": None,
                "analysis_status": "pending",
                "vacancies_count": 0,
                "created_at": None,
            },
        ]
        mock_client.table.return_value.upsert.return_value.execute.return_value = mock_response

        with patch("job_finder.db.posts.get_supabase_client", return_value=mock_client):
            from job_finder.db.posts import create_posts_batch

            posts = [
                PostCreate(
                    telegram_id=100,
                    channel="@ch",
                    telegram_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                    text_full="Post 1",
                ),
                PostCreate(
                    telegram_id=101,
                    channel="@ch",
                    telegram_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
                    text_full="Post 2",
                ),
            ]
            result = create_posts_batch(posts)

        assert len(result) == 2
        assert result[0].telegram_id == 100
        assert result[1].telegram_id == 101

    def test_create_batch_empty(self) -> None:
        """Should return empty list for empty input."""
        with patch("job_finder.db.posts.get_supabase_client"):
            from job_finder.db.posts import create_posts_batch

            result = create_posts_batch([])

        assert result == []


class TestGetPostById:
    """Tests for get_post_by_id function."""

    def test_get_existing_post(self) -> None:
        """Should return PostDB when post exists."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "telegram_id": 12345,
                "channel": "@ch",
                "telegram_date": "2024-01-15T10:00:00Z",
                "text_full": "Text",
                "source_link": None,
                "links": [],
                "analyzed_at": None,
                "analysis_status": "pending",
                "vacancies_count": 0,
                "created_at": None,
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.posts.get_supabase_client", return_value=mock_client):
            from job_finder.db.posts import get_post_by_id

            result = get_post_by_id(1)

        assert result is not None
        assert result.id == 1

    def test_get_non_existing_post(self) -> None:
        """Should return None when post doesn't exist."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = []
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.posts.get_supabase_client", return_value=mock_client):
            from job_finder.db.posts import get_post_by_id

            result = get_post_by_id(999)

        assert result is None


class TestGetPendingPosts:
    """Tests for get_pending_posts function."""

    def test_get_pending_posts(self) -> None:
        """Should return only posts with pending status."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "telegram_id": 100,
                "channel": "@ch",
                "telegram_date": "2024-01-15T10:00:00Z",
                "text_full": "Pending post",
                "source_link": None,
                "links": [],
                "analyzed_at": None,
                "analysis_status": "pending",
                "vacancies_count": 0,
                "created_at": None,
            }
        ]
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = mock_response

        with patch("job_finder.db.posts.get_supabase_client", return_value=mock_client):
            from job_finder.db.posts import get_pending_posts

            result = get_pending_posts(limit=10)

        assert len(result) == 1
        assert result[0].analysis_status == "pending"


class TestUpdatePostAnalysis:
    """Tests for update_post_analysis function."""

    def test_update_analysis_status(self) -> None:
        """Should update post analysis fields."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [
            {
                "id": 1,
                "telegram_id": 100,
                "channel": "@ch",
                "telegram_date": "2024-01-15T10:00:00Z",
                "text_full": "Text",
                "source_link": None,
                "links": [],
                "analyzed_at": "2024-01-15T11:00:00Z",
                "analysis_status": "completed",
                "vacancies_count": 2,
                "created_at": None,
            }
        ]
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            mock_response
        )

        with patch("job_finder.db.posts.get_supabase_client", return_value=mock_client):
            from job_finder.db.posts import update_post_analysis

            update = PostUpdate(
                analysis_status="completed",
                vacancies_count=2,
                analyzed_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc),
            )
            result = update_post_analysis(1, update)

        assert result is not None
        assert result.analysis_status == "completed"
        assert result.vacancies_count == 2
