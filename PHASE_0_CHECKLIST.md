# HotTakes - Phase 0 Checklist

Use this checklist to get the MVP scaffold running locally.

## Repository and Environment

- [ ] Clone repository
- [ ] Create Python virtual environment
- [ ] Activate virtual environment
- [ ] Install backend dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

## Configuration

- [ ] Copy env template
- [ ] Fill Reddit credentials
- [ ] Confirm DB URL

```powershell
Copy-Item backend/.env.example backend/.env
```

## Optional Bootstrap Generation

- [ ] Run bootstrap script for extra MVP stubs

```powershell
powershell -ExecutionPolicy Bypass -File .\STARTER_BOOTSTRAP.ps1
```

## Backend Run

- [ ] Start API from `backend/`
- [ ] Verify `/health`
- [ ] Open Swagger docs

```powershell
cd backend
uvicorn app.main:app --reload
```

Checks:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## MVP Scope Validation

- [ ] Subreddit set to `r/soccer`
- [ ] History set to 30 days
- [ ] Fetch interval set to 30 minutes
- [ ] Limits: 25k/topic, 1k/post, 2k/fetch
- [ ] 4 stance labels configured

## Done Criteria for Phase 0

- [ ] API starts without import/config errors
- [ ] DB tables are created
- [ ] `/api/topics` endpoint responds
- [ ] Scheduler toggles based on env config
- [ ] Repository docs match current structure
