-- Migration 001: Initial schema for job-finder
-- Creates tables: posts, vacancies, channel_states

-- posts: logging ALL posts from channels
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    channel TEXT NOT NULL,
    telegram_date TIMESTAMPTZ NOT NULL,
    text_full TEXT NOT NULL,
    source_link TEXT,
    links JSONB DEFAULT '[]'::jsonb,
    analyzed_at TIMESTAMPTZ,
    analysis_status TEXT DEFAULT 'pending',  -- pending, completed, failed
    vacancies_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT posts_telegram_unique UNIQUE (channel, telegram_id)
);

-- vacancies: vacancies extracted from posts (1 post = N vacancies)
CREATE TABLE IF NOT EXISTS vacancies (
    id BIGSERIAL PRIMARY KEY,
    post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    title TEXT,
    company TEXT,
    industry TEXT,
    level TEXT,  -- junior/middle/senior/lead/head/other
    location TEXT,
    remote_type TEXT DEFAULT 'unknown',  -- remote/hybrid/onsite/unknown
    salary_min_usd NUMERIC(12, 2),
    salary_max_usd NUMERIC(12, 2),
    salary_raw TEXT,
    language TEXT,  -- en/ru/other
    is_relevant BOOLEAN NOT NULL DEFAULT FALSE,
    relevance_reason TEXT,
    status TEXT DEFAULT 'new',  -- new/saved/applied/interview/rejected/offer
    apply_link TEXT,
    notes TEXT,
    cover_letter TEXT,
    raw_snippet TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- channel_states: replacement for state.json
CREATE TABLE IF NOT EXISTS channel_states (
    channel TEXT PRIMARY KEY,
    last_message_id BIGINT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_posts_channel ON posts(channel);
CREATE INDEX IF NOT EXISTS idx_posts_analysis_status ON posts(analysis_status);
CREATE INDEX IF NOT EXISTS idx_vacancies_post_id ON vacancies(post_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_is_relevant ON vacancies(is_relevant) WHERE is_relevant = TRUE;
CREATE INDEX IF NOT EXISTS idx_vacancies_status ON vacancies(status);

-- Trigger to auto-update updated_at on vacancies
CREATE OR REPLACE FUNCTION update_vacancies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS vacancies_updated_at_trigger ON vacancies;
CREATE TRIGGER vacancies_updated_at_trigger
    BEFORE UPDATE ON vacancies
    FOR EACH ROW
    EXECUTE FUNCTION update_vacancies_updated_at();

-- Trigger to auto-update updated_at on channel_states
CREATE OR REPLACE FUNCTION update_channel_states_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS channel_states_updated_at_trigger ON channel_states;
CREATE TRIGGER channel_states_updated_at_trigger
    BEFORE UPDATE ON channel_states
    FOR EACH ROW
    EXECUTE FUNCTION update_channel_states_updated_at();
