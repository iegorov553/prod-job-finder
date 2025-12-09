from __future__ import annotations

from typing import List

from job_finder.models import VacancyNormalized
from job_finder.resources import messages


def _sort_key(vacancy: VacancyNormalized) -> tuple[int, float]:
    location_priority = 2
    if vacancy.remote_type == "remote":
        location_priority = 0
    elif vacancy.location and "barcelona" in vacancy.location.lower():
        location_priority = 1
    salary_max = vacancy.salary_max_usd or 0.0
    return (location_priority, -salary_max)


def _format_vacancy(index: int, vacancy: VacancyNormalized) -> str:
    lines = [
        f"{index}) **{vacancy.title or 'Product Manager'}**",
    ]
    if vacancy.company:
        lines.append(f"Компания: {vacancy.company}")
    if vacancy.location:
        remote_label = f" ({vacancy.remote_type})" if vacancy.remote_type else ""
        lines.append(f"Локация: {vacancy.location}{remote_label}")
    if vacancy.level:
        lines.append(f"Уровень: {vacancy.level}")
    if vacancy.salary_min_usd or vacancy.salary_max_usd or vacancy.salary_raw:
        salary_parts = []
        if vacancy.salary_min_usd or vacancy.salary_max_usd:
            salary_parts.append(
                f"{vacancy.salary_min_usd or ''}-{vacancy.salary_max_usd or ''} USD".strip("-")
            )
        if vacancy.salary_raw:
            salary_parts.append(vacancy.salary_raw)
        salary_text = " / ".join(part for part in salary_parts if part)
        lines.append(f"Зарплата: {salary_text or 'не указана'}")
    lines.append(f"Язык вакансии: {vacancy.language}")
    source_text = vacancy.source_channel
    if vacancy.source_link:
        source_text = f"{vacancy.source_channel} — [ссылка на пост]({vacancy.source_link})"
    lines.append(f"Источник: {source_text}")
    if vacancy.raw_snippet:
        lines.append("")
        lines.append(f"Кратко: {vacancy.raw_snippet.strip()}")
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
