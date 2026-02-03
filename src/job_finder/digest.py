from __future__ import annotations

from typing import List

from job_finder.models import VacancyNormalized
from job_finder.resources import messages

# Placeholder values from LLM that should be treated as "no data"
_PLACEHOLDER_VALUES = frozenset(
    {
        "unspecified",
        "not specified",
        "salary not specified",
        "unknown",
        "n/a",
        "none",
        "не указана",
        "не указано",
        "",
    }
)


def _is_placeholder(value: str | None) -> bool:
    """Check if value is a placeholder that should be hidden."""
    if not value:
        return True
    return value.strip().lower() in _PLACEHOLDER_VALUES


def _sort_key(vacancy: VacancyNormalized) -> tuple[int, float]:
    location_priority = 2
    if vacancy.remote_type == "remote":
        location_priority = 0
    elif vacancy.location and "barcelona" in vacancy.location.lower():
        location_priority = 1
    salary_max = vacancy.salary_max_usd or 0.0
    return (location_priority, -salary_max)


def _format_salary(salary_min: float | None, salary_max: float | None) -> str:
    """Format salary range in compact form like $80k-120k or $150k+."""

    def fmt(val: float) -> str:
        if val >= 1000:
            return f"${int(val / 1000)}k"
        return f"${int(val)}"

    if salary_min and salary_max:
        return f"{fmt(salary_min)}–{fmt(salary_max)}"
    elif salary_max:
        return f"до {fmt(salary_max)}"
    elif salary_min:
        return f"{fmt(salary_min)}+"
    return ""


def _build_metadata_lines(vacancy: VacancyNormalized) -> list[str]:
    """Build metadata as multiple lines, ~2 values per line for readability."""
    lines: list[str] = []

    # Line 1: Company + Industry
    row1: list[str] = []
    if vacancy.company and not _is_placeholder(vacancy.company):
        row1.append(f"🏢 {vacancy.company}")
    if vacancy.industry and not _is_placeholder(vacancy.industry):
        row1.append(f"🏭 {vacancy.industry}")
    if row1:
        lines.append(" · ".join(row1))

    # Line 2: Location + Level
    row2: list[str] = []
    if vacancy.location and not _is_placeholder(vacancy.location):
        loc = vacancy.location
        if vacancy.remote_type and vacancy.remote_type != "unknown":
            loc += f" ({vacancy.remote_type})"
        row2.append(f"📍 {loc}")
    if vacancy.level and vacancy.level != "other":
        row2.append(f"💼 {vacancy.level.capitalize()}")
    if row2:
        lines.append(" · ".join(row2))

    # Line 3: Language (always shown)
    lang_label = vacancy.language.upper() if vacancy.language != "other" else "Other"
    lines.append(f"🌐 {lang_label}")

    return lines


def _format_vacancy(index: int, vacancy: VacancyNormalized) -> str:
    """Format vacancy in compact emoji-based format."""
    # Header with clickable link
    title = vacancy.title or "Product Manager"
    if vacancy.source_link:
        header = f"{index}) [**{title}**]({vacancy.source_link})"
    else:
        header = f"{index}) **{title}**"

    lines = [header]

    # Metadata lines (grouped by ~2 values per line)
    for meta_line in _build_metadata_lines(vacancy):
        lines.append("   " + meta_line)

    # Salary on separate line (only if present)
    if vacancy.salary_min_usd or vacancy.salary_max_usd:
        salary = _format_salary(vacancy.salary_min_usd, vacancy.salary_max_usd)
        lines.append(f"   💰 {salary}")
    elif vacancy.salary_raw and not _is_placeholder(vacancy.salary_raw):
        lines.append(f"   💰 {vacancy.salary_raw}")

    # Apply link on separate line (only if present)
    if vacancy.apply_link:
        lines.append(f"   🔗 [Откликнуться]({vacancy.apply_link})")

    return "\n".join(lines)


def build_digest(vacancies: List[VacancyNormalized]) -> str:
    if not vacancies:
        return messages.EMPTY_DIGEST
    sorted_vacancies = sorted(vacancies, key=_sort_key)
    parts = [
        messages.DIGEST_HEADER,
        "",
        messages.DIGEST_COUNT.format(count=len(sorted_vacancies)),
        "",
    ]
    for idx, vacancy in enumerate(sorted_vacancies, start=1):
        parts.append(_format_vacancy(idx, vacancy))
        parts.append("\n---\n")
    return "\n".join(parts).rstrip()
