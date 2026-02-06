"""Tests for MarkdownV2-safe digest formatting."""

from __future__ import annotations

from datetime import datetime, timezone

from job_finder import digest
from job_finder.models import VacancyNormalized


def test_build_digest_escapes_special_chars_for_markdown_v2() -> None:
    vacancy = VacancyNormalized(
        id=1,
        is_relevant=True,
        relevance_reason="",
        title="Senior/Lead Product Manager (Growth)",
        company="Algonova",
        industry="EdTech",
        level="lead",
        role=None,
        location="Remote (remote)",
        remote_type="remote",
        salary_min_usd=None,
        salary_max_usd=None,
        salary_raw="Competitive salary",
        language="ru",
        source_channel="@rfoundersjobs",
        source_message_id=555,
        source_link="https://t.me/rfoundersjobs/555",
        apply_link="https://example.com/apply?role=pm",
        raw_snippet="PM role with _growth_ focus.",
        post_date=datetime(2026, 2, 3, tzinfo=timezone.utc),
    )

    text = digest.build_digest([vacancy])

    assert "[*Senior/Lead Product Manager \\(Growth\\)*](https://t.me/rfoundersjobs/555)" in text
    assert "PM role with \\_growth\\_ focus\\." in text
    assert "\\-\\-\\-" in text
