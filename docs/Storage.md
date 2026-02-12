# Storage

## Supabase Tables
- posts: raw Telegram messages, analysis status, and metadata.
  - `links` stores raw URLs extracted from text, entities, and inline buttons.
  - Failure diagnostics are stored in `analysis_error_code`, `analysis_error_message`,
    `analysis_http_status`, `analysis_attempts`, and `analysis_run_id`.
- vacancies: extracted job vacancies, relevance, status, and salary fields.
  - `apply_link` is selected by LLM from post URLs.
  - `links_json` stores vacancy-scoped links as JSON objects: `{ "url": "...", "type": "..." }`.
- post_analysis_attempts: per-post LLM attempt logs for troubleshooting (batch id, attempt no, HTTP
  status, error code/message, and response excerpt).
- channel_states: per-channel last_message_id tracking.
- settings: runtime configuration (channels, scheduler, LLM params, limits, custom_prompt).
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
