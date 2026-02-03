EMPTY_DIGEST = "Сегодня подходящих вакансий не найдено."
DIGEST_HEADER = "Ежедневная подборка вакансий Product Manager"
DIGEST_COUNT = "Найдено релевантных вакансий: {count}"
ERROR_PARSING_BATCH = "Не удалось распарсить ответ модели для батча; посты пропущены."
NO_NEW_MESSAGES = "Новых сообщений нет."

# LLM Settings Commands
LLM_SETTINGS_HEADER = "⚙️ *LLM Настройки*"
LLM_SETTINGS_MODEL = "Модель: `{model}`"
LLM_SETTINGS_TEMPERATURE = "Temperature: `{temperature}`"
LLM_SETTINGS_TEMPERATURE_DEFAULT = "Temperature: _(API default)_"
LLM_SETTINGS_TIMEOUT = "Timeout: `{timeout}` сек"
LLM_SETTINGS_RETRY_MAX = "Retry max: `{retry_max}`"
LLM_SETTINGS_RETRY_BACKOFF = "Retry backoff: `{retry_backoff}`"
LLM_SETTINGS_BATCH = "Posts per batch: `{batch}`"
LLM_SETTINGS_LIMIT = "Posts per run: `{limit}`"
LLM_SETTINGS_LOOKBACK = "Hours lookback: `{lookback}`"

LLM_MODEL_UPDATED = "✅ Модель изменена на `{model}`"
LLM_MODEL_USAGE = "Использование: /llm\\_model <имя модели>\nПример: /llm\\_model gpt-4o"

LLM_TEMP_UPDATED = "✅ Temperature изменена на `{temperature}`"
LLM_TEMP_RESET = "✅ Temperature сброшена на значение по умолчанию API"
LLM_TEMP_USAGE = "Использование: /llm\\_temp <0.0-2.0>\nПример: /llm\\_temp 0.7"
LLM_TEMP_INVALID = "❌ Temperature должна быть от 0.0 до 2.0"

LLM_TIMEOUT_UPDATED = "✅ Timeout изменён на `{timeout}` сек"
LLM_TIMEOUT_USAGE = "Использование: /llm\\_timeout <10-300>\nПример: /llm\\_timeout 120"
LLM_TIMEOUT_INVALID = "❌ Timeout должен быть от 10 до 300 секунд"

LLM_BATCH_UPDATED = "✅ Posts per batch изменён на `{batch}`"
LLM_BATCH_USAGE = "Использование: /llm\\_batch <1-50>\nПример: /llm\\_batch 20"
LLM_BATCH_INVALID = "❌ Batch size должен быть от 1 до 50"

LLM_LIMIT_UPDATED = "✅ Posts per run изменён на `{limit}`"
LLM_LIMIT_USAGE = "Использование: /llm\\_limit <1-500>\nПример: /llm\\_limit 100"
LLM_LIMIT_INVALID = "❌ Run limit должен быть от 1 до 500"

LLM_LOOKBACK_UPDATED = "✅ Hours lookback изменён на `{lookback}`"
LLM_LOOKBACK_USAGE = "Использование: /llm\\_lookback <1-168>\nПример: /llm\\_lookback 48"
LLM_LOOKBACK_INVALID = "❌ Hours lookback должен быть от 1 до 168"

# Prompt Commands
PROMPT_HEADER = "📝 *Системный промпт*"
PROMPT_CURRENT = "Текущий промпт:\n```\n{prompt}\n```"
PROMPT_DEFAULT = "_(Используется промпт по умолчанию)_"
PROMPT_SET_SUCCESS = "✅ Промпт обновлён"
PROMPT_SET_USAGE = "Использование: /prompt\\_set <текст промпта>"
PROMPT_SET_TOO_LONG = "❌ Промпт слишком длинный (макс. 10000 символов)"
PROMPT_RESET_SUCCESS = "✅ Промпт сброшен на значение по умолчанию"

# Settings errors
SETTINGS_DB_UNAVAILABLE = "❌ База данных настроек недоступна"
SETTINGS_UPDATE_ERROR = "❌ Ошибка обновления настроек: {error}"

# Retry Failed Commands
RETRY_FAILED_START = "Повторный анализ {count} failed постов..."
RETRY_FAILED_PROGRESS = "Идёт анализ: {done}/{total}"
RETRY_FAILED_NO_POSTS = "Нет failed постов для повторного анализа"
RETRY_FAILED_RESULT = "Результаты повторного анализа"
RETRY_FAILED_ERROR = "❌ Ошибка повторного анализа: {error}"
RETRY_FAILED_INVALID_LIMIT = "❌ Limit должен быть от 1 до 500"
