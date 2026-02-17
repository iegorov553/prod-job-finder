# Workflow

This describes what happens during a single run execution (via /run or the HTTP API).

## Pipeline Steps
1. Load environment configuration and initialize Supabase.
2. Read dynamic settings (channels, limits, LLM params) from Supabase.
3. Ensure channel state records exist for all configured channels.
4. If pending posts exist (from /retry_failed), analyze them first and skip Telegram fetch.
5. Otherwise, fetch new Telegram posts since last_message_id or within the lookback window.
6. Extract raw links per post from text, Telegram entities, and inline buttons; persist into `posts.links`.
7. Persist posts to the posts table (upsert by channel and telegram_id).
8. Send posts to the LLM in batches and parse multi-vacancy results.
9. If a batch parse fails, retry with smaller chunks (`N -> N/2 -> 1`) to recover partial results.
10. Persist per-post failure diagnostics (`analysis_error_code`, HTTP status, attempts, run id) and attempt logs.
11. Persist vacancies (including `apply_link` and `links_json`) and mark posts as analyzed.
12. Run vacancy enrichment: fetch external pages from vacancy links, extract and LLM-clean vacancy text, and persist enrichment status/diagnostics.
13. Update last_message_id per channel (only when new Telegram posts were fetched).
14. If JobSpy is enabled, run the JobSpy pipeline (see below).
15. Query new relevant vacancies (from both Telegram and JobSpy) and build the digest.
16. Persist run status and digest to the runs table.
17. Send the digest to the user via the control bot.

## JobSpy Pipeline Steps
When `jobspy_enabled` is true in settings, the following steps execute after the Telegram pipeline:
1. Read JobSpy configuration from settings (sites, search terms, location, filters).
2. For each search term, call `scrape_jobspy()` to query configured job boards.
3. Deduplicate results by `job_url` within the batch and against existing database records.
4. Insert new results into the `jobspy_jobs` table (upsert with `ON CONFLICT (job_url) DO NOTHING`).
5. Convert each new job to a vacancy with `source_type='jobspy'` and `is_relevant=True`.
6. Insert vacancies into the `vacancies` table.
7. Log pipeline stats (scraped, new, inserted counts).

## Control Bot Responses
- If an analysis run returns an empty message (for example via /retry_failed), the control bot sends a fallback message instead of failing.
- Control bot messages are formatted with Telegram MarkdownV2.

## Run API
- `POST /api/run` creates a new run record with status `running` and triggers the pipeline asynchronously.
- The UI polls the runs table (via Next.js API) to show status and re-enable the Run button.
- A second `POST /api/run` while a run is active returns `409 Conflict`.

## Preview Mode
- /run_once limits to 5 posts and does not update channel state.

## Concurrency Guard
- The pipeline uses a shared lock to prevent concurrent executions from bot commands, scheduler, and HTTP API.
- The lock supports re-entrancy inside the same async task, so background `/api/run` execution does not deadlock when nested pipeline helpers are called.
