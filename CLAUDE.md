# PM Telegram Job Digester

- Purpose: Telegram user-bot that collects channel posts, filters via LLM for a Product Manager profile (middle/senior/lead; remote or Barcelona; EN/RU; ~100k+ USD), and sends a daily Markdown digest to Saved Messages.
- Entry point: `main.py`.
- Core modules: `src/job_finder/config.py`, `state.py`, `scraper.py`, `llm_client.py`, `digest.py`, `models.py`, `resources/messages.py`.
- State: JSON file (`STATE_PATH`, default `state.json`) storing `last_message_id` per channel.
- Setup & usage: see `README.md`; environment template in `.env.example`; Docker build in `Dockerfile`.
