import base64
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import main as main_module

from job_finder.config import Config
from job_finder.db.models import (
    PostAnalysisResult,
    PostDB,
    VacancyDB,
    VacancyEnrichmentUpdate,
    VacancyFromLLM,
)


def test_ensure_session_file(tmp_path) -> None:
    session_bytes = b"dummy"
    encoded = base64.b64encode(session_bytes).decode()
    session_name = "telegram_session"
    # run helper
    main_module._ensure_session_file(session_name, encoded, None, tmp_path)
    session_path = tmp_path / f"{session_name}.session"
    assert session_path.exists()
    assert session_path.read_bytes() == session_bytes


def test_ensure_session_file_with_string_session(tmp_path) -> None:
    """String session should skip file creation."""
    session_name = "telegram_session"
    # With string_session, no file should be created
    main_module._ensure_session_file(session_name, None, "string_session_value", tmp_path)
    session_path = tmp_path / f"{session_name}.session"
    assert not session_path.exists()


def test_ensure_session_file_already_exists(tmp_path) -> None:
    """Existing session file should not be overwritten."""
    session_name = "telegram_session"
    session_path = tmp_path / f"{session_name}.session"
    original_content = b"original"
    session_path.write_bytes(original_content)

    new_encoded = base64.b64encode(b"new_content").decode()
    main_module._ensure_session_file(session_name, new_encoded, None, tmp_path)

    # Original content should be preserved
    assert session_path.read_bytes() == original_content


def test_run_once_calls_vacancy_enrichment(monkeypatch) -> None:
    config = Config(
        telegram_api_id=1,
        telegram_api_hash="hash",
        telegram_session="session",
        telegram_session_base64=None,
        telegram_string_session=None,
        llm_api_key="llm-key",
        llm_base_url="https://llm.example/v1",
        bot_token="token",
        allowed_user_ids=[1],
        supabase_url="https://supabase.example",
        supabase_key="supabase-key",
        api_enabled=False,
        api_host="0.0.0.0",
        api_port=8000,
        run_api_token=None,
    )

    settings_manager = SimpleNamespace(
        get_processing_limits=lambda: {
            "hours_lookback": 24,
            "max_posts_per_run": 30,
            "max_posts_per_batch": 10,
        },
        get_custom_prompt=lambda: "prompt",
        get_llm_config=lambda: {
            "model_name": "gpt-4.1-mini",
            "temperature": None,
            "timeout": 30,
            "retry_max": 1,
            "retry_backoff": 1.0,
        },
        get_jobspy_enabled=lambda: False,
    )

    pending_post = PostDB(
        id=1,
        telegram_id=100,
        channel="@test",
        telegram_date=datetime.now(timezone.utc),
        text_full="Post text",
        source_link="https://t.me/test/100",
        links=["https://jobs.example/apply"],
        analysis_status="pending",
        vacancies_count=0,
    )

    vacancy_from_llm = VacancyFromLLM(
        is_relevant=True,
        relevance_reason="match",
        title="PM",
        company="Acme",
        industry="Tech",
        level="middle",
        location="Remote",
        remote_type="remote",
        salary_min_usd=100000,
        salary_max_usd=130000,
        salary_raw="$100k-$130k",
        language="en",
        raw_snippet="snippet",
        apply_link="https://jobs.example/apply",
        links_json=[],
    )

    created_vacancy = VacancyDB(
        id=10,
        post_id=1,
        title="PM",
        company="Acme",
        industry="Tech",
        level="middle",
        location="Remote",
        remote_type="remote",
        salary_min_usd=Decimal("100000"),
        salary_max_usd=Decimal("130000"),
        salary_raw="$100k-$130k",
        language="en",
        is_relevant=True,
        relevance_reason="match",
        status="new",
        apply_link="https://jobs.example/apply",
        links_json=[],
        notes=None,
        cover_letter=None,
        raw_snippet="snippet",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    monkeypatch.setattr("job_finder.db.posts.get_pending_posts", lambda limit: [pending_post])
    monkeypatch.setattr(
        main_module.llm_client,
        "analyze_posts_db",
        lambda *args, **kwargs: [PostAnalysisResult(post_id=1, vacancies=[vacancy_from_llm])],
    )
    monkeypatch.setattr(main_module, "create_vacancies_batch", lambda vacancies: [created_vacancy])
    monkeypatch.setattr(main_module, "mark_posts_analyzed", lambda *args, **kwargs: 1)
    monkeypatch.setattr(main_module, "get_running_run", lambda: None)
    monkeypatch.setattr(
        main_module.digest_service,
        "build_digest_from_db",
        lambda limit=100: "digest",
    )

    def fake_enrich(vacancies, enrichment_config):
        assert vacancies == [created_vacancy]
        assert enrichment_config.api_key == "llm-key"
        return [
            VacancyEnrichmentUpdate(
                id=10,
                enrichment_status="success",
                enrichment_attempts=1,
                vacancy_text_full="Vacancy text",
                vacancy_text_source_url="https://jobs.example/apply",
            )
        ]

    captured_updates: dict[str, list[VacancyEnrichmentUpdate]] = {}

    def fake_update_enrichment(updates: list[VacancyEnrichmentUpdate]) -> int:
        captured_updates["items"] = updates
        return len(updates)

    monkeypatch.setattr(main_module, "enrich_vacancies", fake_enrich)
    monkeypatch.setattr(main_module, "update_vacancies_enrichment", fake_update_enrichment)

    import asyncio

    result = asyncio.run(main_module._run_once(config, settings_manager, channels=["@test"]))

    assert result.success is True
    assert captured_updates["items"][0].id == 10
    assert captured_updates["items"][0].enrichment_status == "success"
