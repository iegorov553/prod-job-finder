-- Migration: 002_settings_table
-- Description: Create settings table for dynamic bot configuration
-- Date: 2026-01-30

CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Channels
    channels JSONB DEFAULT '[]'::jsonb NOT NULL,

    -- Scheduler
    scheduler_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    scheduler_time_utc TEXT,  -- HH:MM

    -- LLM config
    llm_model_name TEXT DEFAULT 'gpt-4.1-mini' NOT NULL,
    llm_temperature NUMERIC(3, 2),  -- NULL = API default
    llm_timeout INTEGER DEFAULT 60 NOT NULL,
    llm_retry_max INTEGER DEFAULT 2 NOT NULL,
    llm_retry_backoff NUMERIC(4, 1) DEFAULT 2.0 NOT NULL,

    -- Processing limits
    max_posts_per_batch INTEGER DEFAULT 10 NOT NULL,
    max_posts_per_run INTEGER DEFAULT 30 NOT NULL,
    hours_lookback INTEGER DEFAULT 24 NOT NULL,

    -- Custom prompt (NULL = default SYSTEM_PROMPT_MULTI_VACANCY)
    custom_prompt TEXT,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Singleton constraint (одна запись на инстанс)
CREATE UNIQUE INDEX IF NOT EXISTS idx_settings_singleton ON settings ((true));

-- Auto-update trigger
CREATE OR REPLACE FUNCTION update_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS settings_updated_at_trigger ON settings;
CREATE TRIGGER settings_updated_at_trigger
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_settings_updated_at();

-- Initialize with defaults if empty
INSERT INTO settings (channels, scheduler_enabled)
SELECT '[]'::jsonb, FALSE
WHERE NOT EXISTS (SELECT 1 FROM settings);
