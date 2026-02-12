# Architecture

## High-Level Components
- main.py: application entry point and orchestration.
- src/job_finder/config.py: environment-based credentials and infrastructure config.
- src/job_finder/scraper.py: Telethon client and message collection.
- src/job_finder/link_extraction.py: raw URL extraction from post text, entities, and inline buttons.
- src/job_finder/llm_client.py: LLM request and response handling.
- src/job_finder/digest.py: digest rendering in Markdown.
- src/job_finder/bot_control.py: Telegram Bot API control bot and commands.
- src/job_finder/scheduler.py: daily scheduling of runs.
- src/job_finder/run_service.py: run orchestration, concurrency control, and run status tracking.
- src/job_finder/api/*: FastAPI HTTP endpoints (e.g., /api/run).
- src/job_finder/settings_manager.py: cached access to Supabase settings.
- src/job_finder/db/*: Supabase client and CRUD for posts, vacancies, channel states, settings, runs.
- src/job_finder/db/post_analysis_attempts.py: persistence for per-post LLM attempt diagnostics.
- src/job_finder/resources/messages.py: user-facing strings.
- apps/web: Next.js frontend (Run & Vacancies, Settings).

## External Services
- Telegram API via Telethon for message retrieval.
- Telegram Bot API for control and output.
- LLM API using OpenAI-compatible chat completions.
- Supabase (PostgreSQL) for persistence.
- Vercel for frontend hosting.

## Data Flow Summary
- Telegram posts are fetched, normalized, and stored with raw post links in `posts.links`.
- LLM analysis creates vacancies with `apply_link` and structured `links_json`, then marks posts as analyzed.
- Failed analysis keeps structured diagnostics (`analysis_error_*`) and writes attempt logs to `post_analysis_attempts`.
- Relevant vacancies are normalized and rendered into the digest.
- Each run is tracked in the runs table for UI visibility.
