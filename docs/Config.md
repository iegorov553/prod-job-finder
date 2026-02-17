# Configuration

## Environment Variables
- TELEGRAM_API_ID: Telegram API id.
- TELEGRAM_API_HASH: Telegram API hash.
- TELEGRAM_SESSION: session file name (default telegram_session).
- TELEGRAM_SESSION_BASE64: optional base64 session file content.
- TELEGRAM_STRING_SESSION: optional Telethon StringSession.
- LLM_API_KEY: API key for LLM provider.
- LLM_BASE_URL: base URL for OpenAI-compatible API.
- BOT_TOKEN: Telegram bot token for control bot.
- ALLOW_USER_IDS: comma-separated list of allowed Telegram user ids.
- SUPABASE_URL: Supabase project URL.
- SUPABASE_KEY: Supabase service role key.
- API_ENABLED: enable HTTP API server for /api/run.
- API_HOST: HTTP server bind address (default 0.0.0.0).
- API_PORT: HTTP server port (default 8000 or PORT).
- RUN_API_TOKEN: bearer token for /api/run authentication.

## Frontend Runtime Variables (Vercel)
- SUPABASE_URL: Supabase project URL for Next.js server routes.
- SUPABASE_SERVICE_KEY: Supabase `service_role` key (server-only, never public).
- RUN_API_BASE_URL: public Railway backend URL including protocol (for example `https://<service>.up.railway.app`).
- RUN_API_TOKEN: must match backend `RUN_API_TOKEN` used by Python `/api/run`.

## Dynamic Settings (Supabase)
- Stored in the settings table and managed via Telegram commands.
- Includes channels, scheduler, LLM model and limits, and custom_prompt.
- JobSpy settings (managed via `/jobspy_*` commands or the web UI):
  - `jobspy_enabled`: enable/disable JobSpy pipeline (default: false).
  - `jobspy_sites`: JSON array of active sites, e.g. `["indeed","google"]` (default: `["indeed","google"]`).
  - `jobspy_search_terms`: JSON array of search queries, e.g. `["Product Manager","Senior PM"]`.
  - `jobspy_location`: location filter (optional).
  - `jobspy_country`: country code for Indeed (default: `"USA"`).
  - `jobspy_results_wanted`: max results per search term (default: 20).
  - `jobspy_hours_old`: max age of postings in hours (default: 24).
  - `jobspy_job_type`: job type filter — fulltime, parttime, contract, internship, or null.
  - `jobspy_is_remote`: remote-only filter (optional).

## Related Files
- .env.example: template for environment variables.
- apps/web/.env.example: frontend env template for Vercel.
