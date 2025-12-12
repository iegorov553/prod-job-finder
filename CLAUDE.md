# PM Telegram Job Digester

- Purpose: Telegram user-bot that collects channel posts, filters via LLM for a Product Manager profile (middle/senior/lead; remote or Barcelona; EN/RU; ~100k+ USD), and sends a daily Markdown digest via a Bot API control bot (no Saved Messages).
- Entry point: `main.py` (Telethon + Bot API control + scheduler).
- Core modules: `src/job_finder/config.py`, `state.py`, `settings.py`, `scraper.py`, `llm_client.py`, `digest.py`, `scheduler.py`, `bot_control.py`, `utils/locks.py`, `models.py`, `resources/messages.py`.
- State/settings: JSON files (`STATE_PATH` default `state.json`; `SETTINGS_PATH` default `settings.json`) and `digest_last.md` cache.
- Setup & usage: see `README.md`; environment template in `.env.example`; Docker build in `Dockerfile`.
