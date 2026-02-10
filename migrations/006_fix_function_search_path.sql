-- Migration: 006_fix_function_search_path
-- Description: fix mutable search_path warnings for trigger functions
-- Date: 2026-02-10

ALTER FUNCTION public.update_vacancies_updated_at()
SET search_path = public;

ALTER FUNCTION public.update_channel_states_updated_at()
SET search_path = public;
