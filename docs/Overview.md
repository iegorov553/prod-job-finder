# Overview

Product Manager Telegram Job Digester collects posts from selected Telegram channels, analyzes them with an LLM to extract and filter Product Manager vacancies, stores results in Supabase, and delivers a Markdown digest via a control bot.

## Primary Users
- The bot owner who configures channels and LLM settings.
- Operators who trigger runs, inspect status, and review digests.

## Key Capabilities
- Fetches new Telegram posts per channel with per-channel state tracking.
- Runs LLM analysis to extract multiple vacancies from one post.
- Stores posts, vacancies, and runtime settings in Supabase.
- Produces a daily or on-demand digest in Telegram.

## Boundaries and Non-Goals
- Not a public-facing job board or UI.
- Not a full applicant tracking system; it only tracks lightweight vacancy status.
- Not a general purpose Telegram bot for multiple users.
