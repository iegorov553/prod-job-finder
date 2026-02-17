from __future__ import annotations

from datetime import datetime, timezone

from job_finder.db.models import VacancyDB, VacancyLink
from job_finder.vacancy_enrichment import EnrichmentConfig, build_candidate_urls, enrich_vacancies


def _vacancy(
    vacancy_id: int,
    *,
    apply_link: str | None = "https://jobs.example/apply",
    links_json: list[VacancyLink] | None = None,
) -> VacancyDB:
    return VacancyDB(
        id=vacancy_id,
        post_id=10,
        title="Product Manager",
        company="Acme",
        industry="Tech",
        level="middle",
        location="Remote",
        remote_type="remote",
        salary_min_usd=None,
        salary_max_usd=None,
        salary_raw=None,
        language="en",
        is_relevant=True,
        relevance_reason="match",
        status="new",
        apply_link=apply_link,
        links_json=links_json or [],
        notes=None,
        cover_letter=None,
        raw_snippet="snippet",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _config() -> EnrichmentConfig:
    return EnrichmentConfig(
        api_key="test-key",
        base_url="https://llm.example/v1",
        model_name="gpt-5-nano",
        timeout=30,
        max_http_requests_per_vacancy=4,
        max_hops=2,
        http_timeout=10,
        http_retry_max=0,
    )


def test_build_candidate_urls_prioritizes_apply_link_and_deduplicates() -> None:
    vacancy = _vacancy(
        1,
        apply_link="https://jobs.example/apply",
        links_json=[
            VacancyLink(url="https://jobs.example/apply", type="apply_direct"),
            VacancyLink(url="https://jobs.example/description", type="job_description"),
        ],
    )
    result = build_candidate_urls(vacancy)
    assert result == ["https://jobs.example/apply", "https://jobs.example/description"]


def test_enrich_vacancies_success_on_first_url(monkeypatch) -> None:
    vacancy = _vacancy(1)

    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._fetch_html",
        lambda *args, **kwargs: "<html><body>raw</body></html>",
    )
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._extract_main_text",
        lambda html: "Raw vacancy text from page",
    )
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._clean_text_with_llm",
        lambda *args, **kwargs: "Clean vacancy text",
    )
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._extract_links_from_html",
        lambda *args, **kwargs: [],
    )

    result = enrich_vacancies([vacancy], _config())
    assert len(result) == 1
    assert result[0].id == vacancy.id
    assert result[0].enrichment_status == "success"
    assert result[0].vacancy_text_full == "Clean vacancy text"
    assert result[0].vacancy_text_source_url == "https://jobs.example/apply"
    assert result[0].enrichment_error is None
    assert result[0].enrichment_attempts == 1
    assert result[0].enrichment_completed_at is not None


def test_enrich_vacancies_uses_second_hop_selected_by_llm(monkeypatch) -> None:
    vacancy = _vacancy(1, apply_link="https://jobs.example/apply")
    calls: list[str] = []

    def fake_fetch_html(url: str, *args, **kwargs) -> str:
        calls.append(url)
        if url == "https://jobs.example/apply":
            return "<a href='https://jobs.example/full-description'>Read full job</a>"
        return "<html><body>full description</body></html>"

    def fake_extract_main_text(html: str) -> str:
        if "Read full job" in html:
            return "Navigation text"
        return "Full vacancy text from second page"

    def fake_clean_text_with_llm(raw_text: str, *args, **kwargs) -> str:
        if raw_text == "Navigation text":
            return ""
        return "Clean final text"

    monkeypatch.setattr("job_finder.vacancy_enrichment._fetch_html", fake_fetch_html)
    monkeypatch.setattr("job_finder.vacancy_enrichment._extract_main_text", fake_extract_main_text)
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._extract_links_from_html",
        lambda *args, **kwargs: ["https://jobs.example/full-description"],
    )
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._select_second_hop_url",
        lambda *args, **kwargs: "https://jobs.example/full-description",
    )
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._clean_text_with_llm",
        fake_clean_text_with_llm,
    )

    result = enrich_vacancies([vacancy], _config())
    assert result[0].enrichment_status == "success"
    assert result[0].vacancy_text_source_url == "https://jobs.example/full-description"
    assert result[0].enrichment_attempts == 2
    assert calls == ["https://jobs.example/apply", "https://jobs.example/full-description"]


def test_enrich_vacancies_respects_http_request_limit(monkeypatch) -> None:
    vacancy = _vacancy(
        1,
        apply_link="https://jobs.example/apply",
        links_json=[
            VacancyLink(url="https://jobs.example/1", type="other"),
            VacancyLink(url="https://jobs.example/2", type="other"),
            VacancyLink(url="https://jobs.example/3", type="other"),
        ],
    )
    attempts = {"count": 0}

    def fake_fetch_html(*args, **kwargs) -> str:
        attempts["count"] += 1
        return "<html><body>no vacancy</body></html>"

    monkeypatch.setattr("job_finder.vacancy_enrichment._fetch_html", fake_fetch_html)
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._extract_main_text",
        lambda html: "navigation only",
    )
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._clean_text_with_llm",
        lambda *args, **kwargs: "",
    )
    monkeypatch.setattr(
        "job_finder.vacancy_enrichment._extract_links_from_html",
        lambda *args, **kwargs: [],
    )

    config = _config()
    config.max_http_requests_per_vacancy = 2
    result = enrich_vacancies([vacancy], config)
    assert result[0].enrichment_status == "failed"
    assert result[0].enrichment_attempts == 2
    assert attempts["count"] == 2
    assert result[0].vacancy_text_full is None
    assert result[0].enrichment_error is not None
