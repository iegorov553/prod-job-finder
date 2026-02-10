# Frontend

## Overview
The frontend is a Next.js (App Router) application deployed on Vercel. It provides two screens:
- **Run & Vacancies**: trigger a pipeline run, monitor recent runs, and update vacancy statuses.
- **Settings**: manage all dynamic settings stored in Supabase.

## Location
`apps/web`

## Environment Variables
Create a `.env.local` in `apps/web/` using `apps/web/.env.example`:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` (must be Supabase `service_role` key)
- `RUN_API_BASE_URL` (must include protocol, e.g. `https://prod-job-finder-staging.up.railway.app`)
- `RUN_API_TOKEN`

Vercel deployment notes:
- Set `Framework Preset` to `Next.js`.
- Set `Root Directory` to `apps/web`.
- Leave `Output Directory` empty (do not set it to `public`).

## API Routes (Next.js)
- `GET /api/settings`
- `PUT /api/settings`
- `GET /api/vacancies`
- `PATCH /api/vacancies/:id`
- `GET /api/runs`
- `POST /api/run` (proxy to Python API)

## Run Status
Runs are stored in the `runs` table with `running/success/failed` status. The UI polls `/api/runs` to keep the Run button state in sync.

## Troubleshooting
- `TypeError: Failed to parse URL ...` for Run button:
  `RUN_API_BASE_URL` is missing `https://`.
- `Application error` on initial page load:
  check Vercel env vars (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `RUN_API_BASE_URL`, `RUN_API_TOKEN`).

## Local Development
From `apps/web`:
```
npm install
npm run dev
```
