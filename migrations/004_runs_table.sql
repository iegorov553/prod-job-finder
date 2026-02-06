-- Migration: 004_runs_table
-- Description: Create runs table for tracking pipeline executions
-- Date: 2026-02-04

CREATE TABLE IF NOT EXISTS runs (
    id BIGSERIAL PRIMARY KEY,
    status TEXT NOT NULL,
    digest_md TEXT,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at DESC);
