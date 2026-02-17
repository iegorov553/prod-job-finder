-- Migration 010: Add vacancy enrichment fields

ALTER TABLE vacancies
    ADD COLUMN IF NOT EXISTS enrichment_status TEXT NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS enrichment_attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS enrichment_error TEXT,
    ADD COLUMN IF NOT EXISTS enrichment_completed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS vacancy_text_full TEXT,
    ADD COLUMN IF NOT EXISTS vacancy_text_source_url TEXT;

CREATE INDEX IF NOT EXISTS idx_vacancies_enrichment_status ON vacancies(enrichment_status);
