# Workflow

This describes what happens during a single run execution (via /run or the HTTP API).

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
11. Persist run status and digest to the runs table.
12. Send the digest to the user via the control bot.

## Control Bot Responses
- If an analysis run returns an empty message (for example via /retry_failed), the control bot sends a fallback message instead of failing.
- Control bot messages are formatted with Telegram MarkdownV2.

## Run API
- `POST /api/run` creates a new run record with status `running` and triggers the pipeline asynchronously.
- The UI polls the runs table (via Next.js API) to show status and re-enable the Run button.

## Preview Mode
- /run_once limits to 5 posts and does not update channel state.
