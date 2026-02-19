# HotTakes - Start Here

This repository is the MVP starter for HotTakes.

## What HotTakes Does

- Ingests Reddit data from `r/soccer`
- Focuses on player performance + transfer discussions
- Classifies comments into `SUPPORT`, `OPPOSE`, `MIXED`, `NEUTRAL`
- Tracks sentiment + toxicity
- Clusters semantically similar arguments (within stance buckets)
- Exposes results through FastAPI endpoints

## MVP Defaults

- History window: last 30 days
- Fetch cadence: every 30 minutes
- Target volume: 80-200 posts, 8,000-30,000 comments
- Limits: 25,000 comments/topic, 1,000 comments/post, 2,000 comments/fetch

## First Steps

1. Read `README.md`
2. Read `SETUP_README.md`
3. Run bootstrap helper:
   - `powershell -ExecutionPolicy Bypass -File .\STARTER_BOOTSTRAP.ps1`
4. Configure `backend/.env`
5. Start backend:
   - `cd backend`
   - `uvicorn app.main:app --reload`

## Key Docs

- `README.md`: high-level overview + quick start
- `SETUP_README.md`: detailed setup/troubleshooting
- `PROJECT_SPECIFICATION.md`: MVP technical specification
- `PHASE_0_CHECKLIST.md`: execution checklist

## Current Status

- Backend scaffold: present
- Routes/models/config: present
- Scheduler/service jobs: scaffolded
- Frontend: scaffold directory only

Next implementation focus: `backend/app/services/` and `backend/app/tasks/*_job.py`.
