# HotTakes - Files Summary

## Root

- `README.md`: project overview and quick start
- `SETUP_README.md`: detailed setup and troubleshooting
- `PROJECT_SPECIFICATION.md`: MVP technical specification
- `PHASE_0_CHECKLIST.md`: implementation checklist
- `STARTER_BOOTSTRAP.ps1`: starter scaffolding script
- `docker-compose.yml`: local multi-service run

## Backend

- `backend/Dockerfile`: backend container image
- `backend/requirements.txt`: Python dependencies
- `backend/.env.example`: environment template

### App Core

- `backend/app/main.py`: FastAPI app entry + route wiring
- `backend/app/config.py`: settings model
- `backend/app/database.py`: SQLAlchemy setup
- `backend/app/models.py`: ORM models

### Routes

- `backend/app/routes/health.py`
- `backend/app/routes/topics.py`
- `backend/app/routes/comments.py`
- `backend/app/routes/clusters.py`
- `backend/app/routes/timeline.py`

### Tasks and Services

- `backend/app/tasks/scheduler.py`: APScheduler wiring
- `backend/app/tasks/*.py`: periodic job wrappers (generated via bootstrap)
- `backend/app/services/*.py`: fetch/classify/cluster service modules (MVP build area)

### Tests

- `backend/tests/`: backend tests

## Frontend

- `frontend/`: placeholder workspace (MVP frontend to implement)

## Docs Legacy Files

- `00_START_HERE.md`, `COMPLETE_SUMMARY.md`, `FINAL_DELIVERY.md`, `FILE_STRUCTURE.md`
- These are maintained as concise internal references and aligned with current structure.
