# Overview

Product Manager Job Digester collects vacancies from two parallel sources — Telegram channels and job boards (LinkedIn, Indeed, Glassdoor, Google Jobs via JobSpy) — analyzes them, stores results in Supabase, delivers a Markdown digest via a control bot, and provides a web UI for runs, settings, and vacancy status updates.

## Primary Users
- The bot owner who configures channels, job board searches, and LLM settings.
- Operators who trigger runs, inspect status, and review digests.

## Key Capabilities
- Fetches new Telegram posts per channel with per-channel state tracking.
- Runs LLM analysis to extract multiple vacancies from Telegram posts.
- Scrapes job boards via JobSpy (LinkedIn, Indeed, Glassdoor, Google Jobs) with configurable search terms and filters.
- Stores posts, job board results, vacancies, and runtime settings in Supabase.
- Produces a daily or on-demand digest combining both sources in Telegram.
- Provides a Next.js UI to trigger runs and manage vacancy statuses.

## Boundaries and Non-Goals
- Not a public-facing job board.
- Not a full applicant tracking system; it only tracks lightweight vacancy status.
- Not a general purpose Telegram bot for multiple users.
