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

## Dynamic Settings (Supabase)
- Stored in the settings table and managed via Telegram commands.
- Includes channels, scheduler, LLM model and limits, and custom_prompt.

## Related Files
- .env.example: template for environment variables.
