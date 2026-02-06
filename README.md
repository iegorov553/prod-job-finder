# Documentation Index

This folder describes how the Product Manager Telegram Job Digester works and how to operate or change it.

## Start Here
- If you are new to the project: read Overview.md then Architecture.md.
- If you need the processing flow or are debugging a run: read Workflow.md.
- If you are changing data storage or schema: read Storage.md.
- If you are configuring environments or bot settings: read Config.md.
- If you are working on the UI: read Frontend.md.

## Quick Links
- Overview.md
- Architecture.md
- Workflow.md
- Storage.md
- Config.md
- Frontend.md

## System Snapshot
- Entry point: main.py
- Core package: src/job_finder/
- Frontend: apps/web (Next.js on Vercel)
- External services: Telegram (Telethon), LLM API (OpenAI compatible), Supabase (PostgreSQL)
- Persistent data: Supabase tables defined in migrations/*.sql
- Local outputs: relevant_log.jsonl, llm_logs/
- Dependencies: managed via pyproject.toml (Poetry); requirements.txt is not used
