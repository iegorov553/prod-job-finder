EMPTY_DIGEST = "Сегодня подходящих вакансий не найдено."
DIGEST_HEADER = "Ежедневная подборка вакансий Product Manager"
DIGEST_COUNT = "Найдено релевантных вакансий: {count}"
APPLY_LINK_LABEL = "Откликнуться"
ERROR_PARSING_BATCH = "Не удалось распарсить ответ модели для батча; посты пропущены."
NO_NEW_MESSAGES = "Новых сообщений нет."
ACCESS_DENIED = "Access denied."
DIGEST_NOT_FOUND = "Дайджестов пока нет."
EMPTY_RESULT = "Результаты отсутствуют."

# LLM Settings Commands
LLM_SETTINGS_HEADER = "⚙️ LLM Настройки"
LLM_SETTINGS_MODEL = "Модель"
LLM_SETTINGS_TEMPERATURE = "Temperature"
LLM_SETTINGS_TEMPERATURE_DEFAULT = "API default"
LLM_SETTINGS_TIMEOUT = "Timeout"
LLM_SETTINGS_RETRY_MAX = "Retry max"
LLM_SETTINGS_RETRY_BACKOFF = "Retry backoff"
LLM_SETTINGS_BATCH = "Posts per batch"
LLM_SETTINGS_LIMIT = "Posts per run"
LLM_SETTINGS_LOOKBACK = "Hours lookback"

LLM_MODEL_UPDATED = "✅ Модель изменена на {model}"
LLM_MODEL_USAGE = "Использование: /llm_model <имя модели>\nПример: /llm_model gpt-4o"

LLM_TEMP_UPDATED = "✅ Temperature изменена на {temperature}"
LLM_TEMP_RESET = "✅ Temperature сброшена на значение по умолчанию API"
LLM_TEMP_USAGE = "Использование: /llm_temp <0.0-2.0>\nПример: /llm_temp 0.7"
LLM_TEMP_INVALID = "❌ Temperature должна быть от 0.0 до 2.0"

LLM_TIMEOUT_UPDATED = "✅ Timeout изменён на {timeout} сек"
LLM_TIMEOUT_USAGE = "Использование: /llm_timeout <10-300>\nПример: /llm_timeout 120"
LLM_TIMEOUT_INVALID = "❌ Timeout должен быть от 10 до 300 секунд"

LLM_BATCH_UPDATED = "✅ Posts per batch изменён на {batch}"
LLM_BATCH_USAGE = "Использование: /llm_batch <1-50>\nПример: /llm_batch 20"
LLM_BATCH_INVALID = "❌ Batch size должен быть от 1 до 50"

LLM_LIMIT_UPDATED = "✅ Posts per run изменён на {limit}"
LLM_LIMIT_USAGE = "Использование: /llm_limit <1-500>\nПример: /llm_limit 100"
LLM_LIMIT_INVALID = "❌ Run limit должен быть от 1 до 500"

LLM_LOOKBACK_UPDATED = "✅ Hours lookback изменён на {lookback}"
LLM_LOOKBACK_USAGE = "Использование: /llm_lookback <1-168>\nПример: /llm_lookback 48"
LLM_LOOKBACK_INVALID = "❌ Hours lookback должен быть от 1 до 168"

# Prompt Commands
PROMPT_HEADER = "📝 Системный промпт"
PROMPT_DEFAULT = "Используется промпт по умолчанию"
PROMPT_SET_SUCCESS = "✅ Промпт обновлён"
PROMPT_SET_USAGE = "Использование: /prompt_set <текст промпта>"
PROMPT_SET_TOO_LONG = "❌ Промпт слишком длинный (макс. 10000 символов)"
PROMPT_RESET_SUCCESS = "✅ Промпт сброшен на значение по умолчанию"

# Settings errors
SETTINGS_DB_UNAVAILABLE = "❌ База данных настроек недоступна"
SETTINGS_UPDATE_ERROR = "❌ Ошибка обновления настроек: {error}"
HISTORY_EMPTY = "История пуста."
RUN_ALREADY_RUNNING = "Запуск уже выполняется."

# Retry Failed Commands
RETRY_FAILED_START = "Повторный анализ {count} failed постов..."
RETRY_FAILED_PROGRESS = "Идёт анализ: {done}/{total}"
RETRY_FAILED_NO_POSTS = "Нет failed постов для повторного анализа"
RETRY_FAILED_RESULT = "Результаты повторного анализа"
RETRY_FAILED_ERROR = "❌ Ошибка повторного анализа: {error}"
RETRY_FAILED_INVALID_LIMIT = "❌ Limit должен быть от 1 до 500"
PROMPT_NOT_CONFIGURED = "Error: custom_prompt not configured. Use /prompt_set to configure."
LLM_PARSE_ERROR = "LLM rate limit or parse error. Please try again later."
PIPELINE_ERROR = "Pipeline error: {error}"

HELP_GENERAL = [
    "/help - эта справка",
    "/status - статус каналов и расписания",
    "/channels - текущий список каналов",
    "/channels_add @a @b - добавить каналы",
    "/channels_remove @a - убрать каналы",
    "/run - запустить сбор сейчас",
    "/run_once - тестовый сбор (до 5 постов, без обновления состояния)",
    "/retry_failed [limit] - повторить анализ failed постов",
    "/history - последние сохранённые релевантные вакансии",
    "/digest - показать последний дайджест",
    "/schedule - показать расписание",
    "/schedule_set HH:MM - ежедневный запуск по UTC",
    "/schedule_off - выключить автозапуск",
]

HELP_LLM_HEADER = "LLM настройки:"
HELP_LLM = [
    "/llm - показать текущие настройки",
    "/llm_model <name> - изменить модель",
    "/llm_temp <0.0-2.0> - изменить temperature",
    "/llm_timeout <10-300> - изменить timeout",
    "/llm_batch <1-50> - изменить batch size",
    "/llm_limit <1-500> - изменить run limit",
    "/llm_lookback <1-168> - изменить hours lookback",
]

HELP_PROMPT_HEADER = "Промпт:"
HELP_PROMPT = [
    "/prompt - показать текущий промпт",
    "/prompt_set <text> - установить промпт",
    "/prompt_reset - сбросить к дефолтному",
]
