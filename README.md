# Product Manager Telegram Job Digester

Daily one-shot Telegram user-bot that fetches posts from specified channels, sends them to an LLM for relevance filtering/normalization, and delivers a single Markdown digest to your Saved Messages.

## Features
- Telethon user-bot: fetches new posts per channel, tracks `last_message_id`.
- LLM filtering for a single Product Manager profile (middle/senior/lead, remote or Barcelona, EN/RU, ~100k+ USD).
- Minimal state in `state.json`.
- One run = full cycle (fetch → analyze → digest → send), suitable for Railway cron.

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
MAX_POSTS_PER_BATCH=10
HOURS_LOOKBACK=24
STATE_PATH=state.json
SETTINGS_PATH=settings.json
```
See `.env.example` for a ready template.

## Local Setup
1. Install dependencies (Poetry recommended):
   - `poetry install` (installs main + dev tools) or `pip install -r requirements.txt`.
2. Initialize Telethon session (first run will ask for Telegram code/password):
   - `python main.py` and follow prompts to store the session file (`TELEGRAM_SESSION`).
3. Run the bot once:
   - `python main.py`

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
3. Запускайте сервис как долгоживущий процесс (Bot API polling + Telethon). Не используйте Railway cron одновременно с внутренним расписанием.

## Notes
- Channels are configurable via `TELEGRAM_CHANNELS`.
- LLM endpoint/model are configurable via `LLM_BASE_URL` and `LLM_MODEL_NAME`.
- State persists in `STATE_PATH` (JSON). Delete the file to rescan all messages.
- Bot control settings persist in `SETTINGS_PATH`. Autostart schedule is configured via bot commands `/schedule_set HH:MM` (UTC) and `/schedule_off`.
