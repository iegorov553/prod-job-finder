-- Migration 007: add structured vacancy links

ALTER TABLE vacancies
ADD COLUMN IF NOT EXISTS links_json JSONB NOT NULL DEFAULT '[]'::jsonb;
