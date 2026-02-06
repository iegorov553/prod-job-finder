# Storage

## Supabase Tables
- posts: raw Telegram messages, analysis status, and metadata.
- vacancies: extracted job vacancies, relevance, status, and salary fields.
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
