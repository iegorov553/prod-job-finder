from job_finder import digest
from job_finder.models import VacancyNormalized
from job_finder.resources import messages


def _sample_vacancy(**kwargs):
    base = dict(
        id=1,
        is_relevant=True,
        relevance_reason="relevant",
        title="Senior PM",
        company="Acme",
        industry=None,
        level="senior",
        role="Product Manager",
        location="Remote",
        remote_type="remote",
        salary_min_usd=100000,
        salary_max_usd=120000,
        salary_raw=None,
        language="en",
        source_channel="@a",
        source_message_id=10,
        source_link="https://t.me/a/10",
        apply_link=None,
        raw_snippet="Desc",
        post_date=None,
    )
    base.update(kwargs)
    return VacancyNormalized(**base)


def test_empty_digest() -> None:
    assert digest.build_digest([]) == messages.EMPTY_DIGEST


def test_digest_sorts_remote_first() -> None:
    remote = _sample_vacancy(id=1, location="Remote", remote_type="remote", salary_max_usd=120000)
    barcelona = _sample_vacancy(
        id=2,
        location="Barcelona office",
        remote_type="onsite",
        salary_max_usd=130000,
    )
    onsite = _sample_vacancy(id=3, location="Berlin", remote_type="onsite", salary_max_usd=150000)
    result = digest.build_digest([onsite, barcelona, remote])
    lines = result.splitlines()
    # First vacancy should be remote (line 4 contains "1)")
    assert "1)" in lines[4]
    # Check that Remote appears in the first vacancy block
    first_block = "\n".join(lines[4:8])
    assert "Remote" in first_block


def test_format_vacancy_compact_format() -> None:
    """Test that vacancy uses new compact emoji format with multi-line metadata."""
    vacancy = _sample_vacancy(
        title="Product Manager",
        company="TechCorp",
        industry="EdTech",
        location="Berlin",
        remote_type="hybrid",
        level="senior",
        language="en",
        salary_min_usd=80000,
        salary_max_usd=120000,
        apply_link="https://apply.example.com",
        source_link="https://t.me/jobs/123",
    )
    result = digest._format_vacancy(1, vacancy)

    # Header should be clickable link with bold (single asterisks for Telegram Markdown)
    assert "[*Product Manager*](https://t.me/jobs/123)" in result
    # Emoji metadata (split into multiple lines)
    assert "🏢 TechCorp" in result
    assert "🏭 EdTech" in result
    assert "📍 Berlin (hybrid)" in result
    assert "💼 Senior" in result
    assert "🌐 EN" in result
    # Company and Industry should be on same line
    assert "🏢 TechCorp · 🏭 EdTech" in result
    # Location and Level should be on same line
    assert "📍 Berlin (hybrid) · 💼 Senior" in result
    # Salary on separate line
    assert "💰 $80k–$120k" in result
    # Language should be on same line (no date in this test)
    assert "🌐 EN" in result
    # Apply link on separate line
    assert "🔗 [Откликнуться](https://apply.example.com)" in result


def test_format_vacancy_hides_unknown_remote_type() -> None:
    """Test that unknown remote_type is not shown in parentheses."""
    vacancy = _sample_vacancy(location="NYC", remote_type="unknown")
    result = digest._format_vacancy(1, vacancy)
    # Should show location without "(unknown)"
    assert "📍 NYC" in result
    assert "(unknown)" not in result


def test_format_vacancy_hides_other_level() -> None:
    """Test that level='other' is not shown."""
    vacancy = _sample_vacancy(level="other")
    result = digest._format_vacancy(1, vacancy)
    assert "💼" not in result


def test_format_vacancy_no_salary_when_missing() -> None:
    """Test that salary line is omitted when no salary data."""
    vacancy = _sample_vacancy(salary_min_usd=None, salary_max_usd=None, salary_raw=None)
    result = digest._format_vacancy(1, vacancy)
    assert "💰" not in result
    assert "Зарплата" not in result


def test_format_vacancy_raw_salary_fallback() -> None:
    """Test that raw salary is shown when USD values are missing."""
    vacancy = _sample_vacancy(salary_min_usd=None, salary_max_usd=None, salary_raw="€5000/month")
    result = digest._format_vacancy(1, vacancy)
    assert "💰 €5000/month" in result


def test_format_salary_range() -> None:
    """Test salary formatting helper."""
    assert digest._format_salary(80000, 120000) == "$80k–$120k"
    assert digest._format_salary(None, 100000) == "до $100k"
    assert digest._format_salary(150000, None) == "$150k+"
    assert digest._format_salary(None, None) == ""


def test_is_placeholder() -> None:
    """Test placeholder detection."""
    # Should be placeholders
    assert digest._is_placeholder(None) is True
    assert digest._is_placeholder("") is True
    assert digest._is_placeholder("unspecified") is True
    assert digest._is_placeholder("Unspecified") is True
    assert digest._is_placeholder("not specified") is True
    assert digest._is_placeholder("salary not specified") is True
    assert digest._is_placeholder("unknown") is True
    assert digest._is_placeholder("n/a") is True
    assert digest._is_placeholder("не указана") is True
    # Should NOT be placeholders
    assert digest._is_placeholder("Berlin") is False
    assert digest._is_placeholder("$100k") is False
    assert digest._is_placeholder("Remote") is False


def test_format_vacancy_hides_unspecified_location() -> None:
    """Test that 'unspecified' location is hidden."""
    vacancy = _sample_vacancy(location="unspecified", remote_type="remote")
    result = digest._format_vacancy(1, vacancy)
    assert "📍" not in result
    assert "unspecified" not in result


def test_format_vacancy_hides_salary_not_specified() -> None:
    """Test that 'salary not specified' is hidden."""
    vacancy = _sample_vacancy(
        salary_min_usd=None, salary_max_usd=None, salary_raw="salary not specified"
    )
    result = digest._format_vacancy(1, vacancy)
    assert "💰" not in result
    assert "salary not specified" not in result


def test_format_vacancy_shows_post_date() -> None:
    """Test that post_date is shown in DD.MM.YYYY format with language on same line."""
    from datetime import datetime, timezone

    vacancy = _sample_vacancy(post_date=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc))
    result = digest._format_vacancy(1, vacancy)
    assert "📅 15.01.2025" in result
    # Date and language should be on same line
    assert "📅 15.01.2025 · 🌐 EN" in result


def test_format_vacancy_hides_missing_post_date() -> None:
    """Test that post_date line is omitted when date is None."""
    vacancy = _sample_vacancy(post_date=None)
    result = digest._format_vacancy(1, vacancy)
    assert "📅" not in result


def test_format_vacancy_shows_raw_snippet() -> None:
    """Test that raw_snippet is shown if present and not placeholder."""
    vacancy = _sample_vacancy(raw_snippet="Looking for experienced PM to lead product strategy")
    result = digest._format_vacancy(1, vacancy)
    assert "📝" in result
    assert "Looking for experienced PM" in result


def test_format_vacancy_hides_unspecified_raw_snippet() -> None:
    """Test that 'unspecified' raw_snippet is hidden."""
    vacancy = _sample_vacancy(raw_snippet="unspecified")
    result = digest._format_vacancy(1, vacancy)
    assert "📝" not in result


def test_format_vacancy_hides_empty_raw_snippet() -> None:
    """Test that empty raw_snippet is hidden."""
    vacancy = _sample_vacancy(raw_snippet="")
    result = digest._format_vacancy(1, vacancy)
    assert "📝" not in result


def test_format_vacancy_field_order() -> None:
    """Test that date/language and description are ordered with a blank line before description."""
    from datetime import datetime, timezone

    vacancy = _sample_vacancy(
        salary_min_usd=100000,
        salary_max_usd=120000,
        post_date=datetime(2025, 1, 15, tzinfo=timezone.utc),
        raw_snippet="Great opportunity",
        apply_link="https://apply.example.com",
    )
    result = digest._format_vacancy(1, vacancy)

    # Find positions
    salary_pos = result.find("💰")
    date_pos = result.find("📅")
    snippet_pos = result.find("📝")
    apply_pos = result.find("🔗")

    # Verify order: salary < date < snippet < apply_link
    assert salary_pos < date_pos < snippet_pos < apply_pos

    # Verify empty line before description
    lines = result.split("\n")
    snippet_line_idx = None
    for i, line in enumerate(lines):
        if "📝" in line:
            snippet_line_idx = i
            break
    assert snippet_line_idx is not None
    assert snippet_line_idx > 0
    # Line before description should be empty
    assert lines[snippet_line_idx - 1].strip() == ""
