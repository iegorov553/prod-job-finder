# Workflow

This describes what happens during a single /run execution.

## Pipeline Steps
1. Load environment configuration and initialize Supabase.
2. Read dynamic settings (channels, limits, LLM params) from Supabase.
3. Ensure channel state records exist for all configured channels.
4. If pending posts exist (from /retry_failed), analyze them first and skip Telegram fetch.
5. Otherwise, fetch new Telegram posts since last_message_id or within the lookback window.
6. Persist posts to the posts table (upsert by channel and telegram_id).
7. Send posts to the LLM in batches and parse multi-vacancy results.
8. Persist vacancies to the vacancies table and mark posts as analyzed.
9. Update last_message_id per channel (only when new Telegram posts were fetched).
10. Query new relevant vacancies and build the digest.
11. Write digest to digest_last.md and send it to the user via the control bot.

## Control Bot Responses
- If an analysis run returns an empty message (for example via /retry_failed), the control bot sends a fallback message instead of failing.

## Preview Mode
- /run_once limits to 5 posts and does not update channel state.
