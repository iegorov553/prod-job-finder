# Storage

## Supabase Tables
- posts: raw Telegram messages, analysis status, and metadata.
  - `links` stores raw URLs extracted from text, entities, and inline buttons.
  - Failure diagnostics are stored in `analysis_error_code`, `analysis_error_message`,
    `analysis_http_status`, `analysis_attempts`, and `analysis_run_id`.
- jobspy_jobs: raw job board results scraped by JobSpy.
  - `site`: source platform (linkedin, indeed, glassdoor, google).
  - `job_url`: unique URL used as deduplication key.
  - Structured fields: `title`, `company`, `location`, `description`, `date_posted`.
  - Salary fields: `salary_min`, `salary_max`, `salary_currency`.
  - `job_type`, `is_remote`: job classification.
  - `search_term`: the query that found this job.
  - `raw_data`: full DataFrame row as JSONB for debugging.
- vacancies: extracted job vacancies, relevance, status, and salary fields.
  - `source_type`: `'telegram'` or `'jobspy'` — indicates the data source.
  - `jobspy_job_id`: references `jobspy_jobs(id)` for JobSpy-sourced vacancies.
  - `post_id`: references `posts(id)` for Telegram-sourced vacancies (nullable).
  - CHECK constraint ensures Telegram vacancies have `post_id` and JobSpy vacancies have `jobspy_job_id`.
  - `apply_link` is selected by LLM from post URLs (Telegram) or is the `job_url` (JobSpy).
  - `links_json` stores vacancy-scoped links as JSON objects: `{ "url": "...", "type": "..." }`.
  - Enrichment fields:
    - `enrichment_status`: `pending|success|failed`.
    - `enrichment_attempts`: number of HTTP attempts performed for enrichment.
    - `enrichment_error`: last enrichment error message (if failed).
    - `enrichment_completed_at`: timestamp of enrichment completion.
    - `vacancy_text_full`: cleaned vacancy text extracted from linked pages.
    - `vacancy_text_source_url`: URL that produced `vacancy_text_full`.
- post_analysis_attempts: per-post LLM attempt logs for troubleshooting (batch id, attempt no, HTTP
  status, error code/message, and response excerpt).
- channel_states: per-channel last_message_id tracking.
- settings: runtime configuration (channels, scheduler, LLM params, limits, custom_prompt, JobSpy config).
- runs: pipeline run history (status, timestamps, digest, error).

## Local Files
- digest_last.md: last generated digest text.
- relevant_log.jsonl: append-only history of relevant items per run.
- llm_logs/: JSON logs for each LLM batch run.

## Migrations
- migrations/001_initial_schema.sql: posts, vacancies, channel_states.
- migrations/002_settings_table.sql: settings table and defaults.
- migrations/003_require_custom_prompt.sql: custom_prompt requirement and default.
- migrations/004_runs_table.sql: runs table for UI and API tracking.
- migrations/007_add_vacancy_links_json.sql: `vacancies.links_json` JSONB column.
- migrations/008_update_default_prompt_with_links.sql: updates legacy default prompt with link typing/output rules.
- migrations/009_post_analysis_diagnostics.sql: post failure diagnostics and
  `post_analysis_attempts` table.
- migrations/010_vacancy_enrichment.sql: vacancy enrichment status and extracted text fields.
- migrations/011_add_jobspy_support.sql: `jobspy_jobs` table, `vacancies` source_type/jobspy_job_id columns, `settings` JobSpy config columns.
