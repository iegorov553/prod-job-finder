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
Populate environment variables (or `.env`):
```
TELEGRAM_API_ID=...
TELEGRAM_API_HASH=...
TELEGRAM_SESSION=telegram_session
# Optional for non-interactive setups: base64-encoded Telethon session file content
# TELEGRAM_SESSION_BASE64=...
# Optional alternative (shorter): Telethon StringSession
# TELEGRAM_STRING_SESSION=...
TELEGRAM_CHANNELS=@channel1,@channel2
BOT_TOKEN=your_bot_token
ALLOW_USER_IDS=123456789  # comma-separated user IDs allowed to control the bot
LLM_API_KEY=...
LLM_MODEL_NAME=gpt-4.1-mini
LLM_BASE_URL=https://api.openai.com/v1
# Optional: temperature (leave empty to use provider default)
# LLM_TEMPERATURE=
# Optional: timeout to LLM in seconds (default 60)
# LLM_TIMEOUT=60
# Optional: retries/backoff on 429/5xx (default max=2, backoff=2.0)
# LLM_RETRY_MAX=2
# LLM_RETRY_BACKOFF=2.0
# Optional: OpenAI Responses prompt id/version (if using hosted prompt)
# LLM_PROMPT_ID=pmpt_xxx
# LLM_PROMPT_VERSION=2
MAX_POSTS_PER_BATCH=10
MAX_POSTS_PER_RUN=30
HOURS_LOOKBACK=24

# Supabase (required)
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
```

### Dynamic Settings via Supabase
You can manage all settings via Telegram bot commands (no restart required):
- **Channels**: add/remove channels dynamically
- **Scheduler**: configure daily run time
- **LLM model**: change model without editing env vars
- **Temperature**: adjust creativity/consistency balance
- **Timeouts & retries**: tune for different API providers
- **Processing limits**: batch size, posts per run, lookback period
- **Custom prompt**: override the default system prompt for LLM

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
3. Control bot commands (in private chat with your Bot API bot):
   - **Basic**: `/status`, `/channels`, `/channels_add @a @b`, `/channels_remove @a`, `/run`, `/run_once`, `/digest`, `/history`
   - **Schedule**: `/schedule`, `/schedule_set HH:MM` (UTC), `/schedule_off`
   - **LLM Settings**: `/llm`, `/llm_model <name>`, `/llm_temp <0.0-2.0>`, `/llm_timeout <10-300>`, `/llm_batch <1-50>`, `/llm_limit <1-500>`, `/llm_lookback <1-168>`
   - **Prompt**: `/prompt`, `/prompt_set <text>`, `/prompt_reset`
4. Service mode: run `PYTHONPATH=src python main.py` (keeps polling Bot API and Telethon).

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
2. Configure environment variables in project settings (see above).
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
3. Run the service as a long-running process (Bot API polling + Telethon). Do not use Railway cron together with internal `/schedule_set` scheduling.

## Notes
- Channels are configurable via `TELEGRAM_CHANNELS` env var (initial list) and `/channels_add` / `/channels_remove` bot commands.
- LLM endpoint/model are configurable via `LLM_BASE_URL` and `LLM_MODEL_NAME`.
- All state is stored in Supabase database.
- Autostart schedule is configured via bot commands `/schedule_set HH:MM` (UTC) and `/schedule_off`.
- If LLM returns invalid/empty JSON for all batches, state is not updated and you will see a "rate limit or parse error" message.
