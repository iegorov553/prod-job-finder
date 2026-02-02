# Product Manager Telegram Job Digester

Daily one-shot Telegram user-bot that fetches posts from specified channels, sends them to an LLM for relevance filtering/normalization, and delivers a single Markdown digest to your Saved Messages.

## Features
- Telethon user-bot: fetches new posts per channel, tracks `last_message_id` in Supabase.
- LLM filtering for a single Product Manager profile (middle/senior/lead, remote or Barcelona, EN/RU, ~100k+ USD).
- **Multi-vacancy extraction**: LLM extracts ALL vacancies from each post (one post can contain multiple jobs).
- **Supabase integration**: stores all posts, vacancies, channel states, and settings in PostgreSQL.
- Bot API control bot: commands to view status, manage channels, trigger runs, and configure daily schedule.
- One run = full cycle (fetch → analyze → digest → send); works as a long-running service (polling Bot API) or manual trigger.

## Configuration

Only credentials are configured via environment variables. All other settings (channels, LLM params, limits) are stored in Supabase and managed via Telegram bot commands.

### Environment Variables

```
# Telegram credentials
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_SESSION=telegram_session
# Optional: base64-encoded Telethon session file or StringSession
# TELEGRAM_SESSION_BASE64=...
# TELEGRAM_STRING_SESSION=...

# LLM API credentials
LLM_API_KEY=...
LLM_BASE_URL=https://api.openai.com/v1

# Bot credentials
BOT_TOKEN=your_bot_token
ALLOW_USER_IDS=123456789  # comma-separated user IDs

# Supabase credentials (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
```

See `.env.example` for a ready template.

## Supabase Setup (Required)

The app requires Supabase for persistent storage:
- `posts`: all fetched Telegram messages
- `vacancies`: extracted job vacancies (multiple per post)
- `channel_states`: tracking last message IDs per channel
- `settings`: dynamic bot configuration (LLM settings, limits, custom prompt, scheduler)

### Database Schema
Run migrations in Supabase SQL Editor (Dashboard → SQL Editor):
```sql
-- See migrations/001_initial_schema.sql for initial schema
-- See migrations/002_settings_table.sql for settings table
-- See migrations/003_require_custom_prompt.sql for prompt requirement
```

### Dynamic Settings via Telegram Bot

All settings are managed via Telegram bot commands (no restart required):

| Setting | Command | Description |
|---------|---------|-------------|
| Channels | `/channels_add @a @b` | Add channels to monitor |
| Channels | `/channels_remove @a` | Remove channels |
| Scheduler | `/schedule_set HH:MM` | Set daily run time (UTC) |
| Scheduler | `/schedule_off` | Disable auto-run |
| LLM Model | `/llm_model gpt-4o` | Change LLM model |
| Temperature | `/llm_temp 0.7` | Set LLM temperature (0.0-2.0) |
| Timeout | `/llm_timeout 120` | Request timeout (10-300 sec) |
| Batch Size | `/llm_batch 5` | Posts per LLM batch (1-50) |
| Run Limit | `/llm_limit 100` | Max posts per run (1-500) |
| Lookback | `/llm_lookback 48` | Hours to look back (1-168) |
| Prompt | `/prompt_set <text>` | Set custom system prompt |
| Prompt | `/prompt_reset` | Reset to default prompt |

### Benefits of Supabase
- Persistent storage across deploys
- Analytics on all historical vacancies
- Track application status per vacancy
- Multi-device access to data
- **Runtime configuration** without redeploying

## Local Setup
1. Install dependencies (Poetry recommended):
   - `poetry install` (installs main + dev tools) or `pip install -r requirements.txt`.
2. Initialize Telethon session (first run will ask for Telegram code/password):
   - `PYTHONPATH=src python main.py` and follow prompts to store the session file (`TELEGRAM_SESSION`).
3. Configure initial settings via Telegram bot:
   - Add channels: `/channels_add @channel1 @channel2`
   - Set prompt: `/prompt_set Your custom prompt...`
4. Run pipeline: `/run` or `/run_once` (preview mode)

## Testing & Quality
- `ruff format .` then `ruff check .`
- `mypy src`
- `pytest`
- Optional security checks: `bandit -c pyproject.toml -r src`, `pip-audit -r requirements.txt`
- Pre-commit: `pre-commit install` to run all hooks locally.

## Docker
```
docker build -t pm-job-digester .
docker run --rm --env-file .env pm-job-digester
```
The image uses Poetry to install deps; tests can run inside the same image.

## Deploy on Railway
1. Push this repo to Railway (use `staging` branch; avoid `main`).
2. Configure environment variables in project settings (credentials only - see above).
   - For non-interactive login, create Telethon session locally once: run `PYTHONPATH=src python main.py`, complete Telegram code/password, then either:
     - base64-encode the generated `TELEGRAM_SESSION.session` file (`base64 -w0 telegram_session.session`) and set `TELEGRAM_SESSION_BASE64`, or
     - generate a short StringSession and set `TELEGRAM_STRING_SESSION` (preferred to avoid size limits):
       ```
       python - <<'PY'
       from telethon.sync import TelegramClient
       from telethon.sessions import StringSession
       api_id = int("YOUR_API_ID")
       api_hash = "YOUR_API_HASH"
       client = TelegramClient("telegram_session", api_id, api_hash)
       client.connect()
       if not client.is_user_authorized():
           raise SystemExit("Session not authorized; run main.py once to login.")
       print(StringSession.save(client.session))
       PY
       ```
   - Alternatively, mount a persistent volume and place the `.session` file there under the configured `TELEGRAM_SESSION` name.
3. Configure channels and settings via Telegram bot commands after first deploy.
4. Run the service as a long-running process (Bot API polling + Telethon). Do not use Railway cron together with internal `/schedule_set` scheduling.

## Notes
- All settings are stored in Supabase database and configured via Telegram bot.
- LLM endpoint is configured via `LLM_BASE_URL` env var (credentials only).
- If LLM returns invalid/empty JSON for all batches, state is not updated and you will see a "rate limit or parse error" message.
