# Architecture

## High-Level Components
- main.py: application entry point and orchestration.
- src/job_finder/config.py: environment-based credentials and infrastructure config.
- src/job_finder/scraper.py: Telethon client and message collection.
- src/job_finder/link_extraction.py: raw URL extraction from post text, entities, and inline buttons.
- src/job_finder/llm_client.py: LLM request and response handling.
- src/job_finder/vacancy_enrichment.py: link-based vacancy text enrichment (`requests` + `trafilatura` + LLM cleanup).
- src/job_finder/jobspy_scraper.py: JobSpy wrapper for multi-platform job board scraping (LinkedIn, Indeed, Glassdoor, Google Jobs).
- src/job_finder/jobspy_pipeline.py: JobSpy pipeline orchestration — scrape, deduplicate, store, convert to vacancies.
- src/job_finder/digest.py: digest rendering in Markdown.
- src/job_finder/digest_service.py: source-aware digest normalization (Telegram and JobSpy).
- src/job_finder/bot_control.py: Telegram Bot API control bot and commands.
- src/job_finder/scheduler.py: daily scheduling of runs.
- src/job_finder/run_service.py: run orchestration, concurrency control, and run status tracking.
- src/job_finder/api/*: FastAPI HTTP endpoints (e.g., /api/run).
- src/job_finder/settings_manager.py: cached access to Supabase settings.
- src/job_finder/db/*: Supabase client and CRUD for posts, vacancies, channel states, settings, runs.
- src/job_finder/db/jobspy_jobs.py: CRUD for jobspy_jobs table (batch upsert, dedup lookup).
- src/job_finder/db/post_analysis_attempts.py: persistence for per-post LLM attempt diagnostics.
- src/job_finder/resources/messages.py: user-facing strings.
- src/job_finder/resources/enrichment_prompts.py: prompt templates for enrichment LLM subtasks.
- apps/web: Next.js frontend (Run & Vacancies, Settings).

## External Services
- Telegram API via Telethon for message retrieval.
- Telegram Bot API for control and output.
- LLM API using OpenAI-compatible chat completions.
- Supabase (PostgreSQL) for persistence.
- Vercel for frontend hosting.

## Data Flow Summary

Two parallel pipelines converge at the `vacancies` table:

```
Pipeline 1 (Telegram):  Telegram → posts → LLM → vacancies
Pipeline 2 (JobSpy):    JobSpy → jobspy_jobs → vacancies
                                                    ↓
                                              digest + UI
```

- **Telegram pipeline**: posts are fetched, normalized, and stored with raw post links in `posts.links`. LLM analysis creates vacancies with `apply_link` and structured `links_json`, then marks posts as analyzed. Enrichment fetches external vacancy pages, extracts text, and persists per-vacancy enrichment status and diagnostics. Failed analysis keeps structured diagnostics (`analysis_error_*`) and writes attempt logs to `post_analysis_attempts`.
- **JobSpy pipeline**: searches job boards with configured search terms, deduplicates results by `job_url`, stores raw results in `jobspy_jobs`, then converts each result into a vacancy with `source_type='jobspy'`. JobSpy vacancies skip LLM analysis (data is already structured).
- Relevant vacancies from both sources are normalized and rendered into the digest.
- Each run is tracked in the runs table for UI visibility.
