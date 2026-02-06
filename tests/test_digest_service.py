"""Tests for building digest on demand from DB."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from job_finder import telegram_markdown as mdv2
from job_finder.db.models import PostDB, VacancyDB
from job_finder.digest_service import build_digest_from_db
from job_finder.resources import messages


def test_build_digest_from_db_empty_returns_empty_digest() -> None:
    with patch("job_finder.digest_service.get_new_relevant_vacancies", return_value=[]):
        assert build_digest_from_db() == mdv2.escape(messages.EMPTY_DIGEST)


def test_build_digest_from_db_uses_post_data() -> None:
    vacancy = VacancyDB(
        id=1,
        post_id=10,
        title="Senior/Lead Product Manager (Growth)",
        company="Algonova",
        industry="EdTech",
        level="lead",
        location="Remote (remote)",
        remote_type="remote",
        salary_min_usd=Decimal("0"),
        salary_raw="Competitive salary",
        language="ru",
        is_relevant=True,
        raw_snippet="PM role with _growth_ focus.",
        apply_link="https://example.com/apply?role=pm",
    )
    post = PostDB(
        id=10,
        telegram_id=555,
        channel="@rfoundersjobs",
        telegram_date=datetime(2026, 2, 3, tzinfo=timezone.utc),
        text_full="Post",
        source_link="https://t.me/rfoundersjobs/555",
        links=[],
    )

    with (
        patch("job_finder.digest_service.get_new_relevant_vacancies", return_value=[vacancy]),
        patch("job_finder.digest_service.get_post_by_id", return_value=post),
    ):
        digest_text = build_digest_from_db()

    assert "https://t.me/rfoundersjobs/555" in digest_text
    assert mdv2.escape("🏢 Algonova") in digest_text
    assert mdv2.escape("📅 03.02.2026") in digest_text
