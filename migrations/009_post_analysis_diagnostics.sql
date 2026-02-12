-- Migration 009: add diagnostics fields for failed post analysis and attempt logs

ALTER TABLE posts
ADD COLUMN IF NOT EXISTS analysis_error_code TEXT,
ADD COLUMN IF NOT EXISTS analysis_error_message TEXT,
ADD COLUMN IF NOT EXISTS analysis_http_status INTEGER,
ADD COLUMN IF NOT EXISTS analysis_attempts INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS analysis_run_id BIGINT REFERENCES runs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_posts_analysis_error_code ON posts(analysis_error_code);
CREATE INDEX IF NOT EXISTS idx_posts_analysis_run_id ON posts(analysis_run_id);

CREATE TABLE IF NOT EXISTS post_analysis_attempts (
    id BIGSERIAL PRIMARY KEY,
    run_id BIGINT REFERENCES runs(id) ON DELETE SET NULL,
    post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    batch_id TEXT,
    attempt_no INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    timeout_sec INTEGER NOT NULL,
    http_status INTEGER,
    error_code TEXT,
    error_message TEXT,
    response_excerpt TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_post_analysis_attempts_run_id
    ON post_analysis_attempts(run_id);
CREATE INDEX IF NOT EXISTS idx_post_analysis_attempts_post_id
    ON post_analysis_attempts(post_id);
CREATE INDEX IF NOT EXISTS idx_post_analysis_attempts_error_code
    ON post_analysis_attempts(error_code);
CREATE INDEX IF NOT EXISTS idx_post_analysis_attempts_created_at
    ON post_analysis_attempts(created_at DESC);

