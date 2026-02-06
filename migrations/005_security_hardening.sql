-- Migration: 005_security_hardening
-- Description: tighten RLS policies and privileges for public tables
-- Date: 2026-02-06

-- 1) Ensure RLS is enabled on all application tables in public schema.
ALTER TABLE IF EXISTS posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS vacancies ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS channel_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS runs ENABLE ROW LEVEL SECURITY;

-- 2) Replace permissive policies scoped to PUBLIC with service_role-only policies.
DROP POLICY IF EXISTS "Service role full access to posts" ON posts;
CREATE POLICY "Service role full access to posts"
ON posts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to vacancies" ON vacancies;
CREATE POLICY "Service role full access to vacancies"
ON vacancies
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to channel_states" ON channel_states;
CREATE POLICY "Service role full access to channel_states"
ON channel_states
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to settings" ON settings;
CREATE POLICY "Service role full access to settings"
ON settings
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

DROP POLICY IF EXISTS "Service role full access to runs" ON runs;
CREATE POLICY "Service role full access to runs"
ON runs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- 3) Fix mutable search_path warning for trigger function.
ALTER FUNCTION public.update_settings_updated_at()
SET search_path = public;

-- 4) Apply least privilege on application tables.
REVOKE ALL ON TABLE posts, vacancies, channel_states, settings, runs FROM anon, authenticated;
