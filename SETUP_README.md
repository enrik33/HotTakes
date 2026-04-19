# HotTakes - Setup Guide

This guide covers setup and running HotTakes locally.

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL 14+ (or SQLite for local dev)
- Git

---

## Quick Start (Local Development)

### 1. Clone & Navigate

```bash
git clone https://github.com/enrik33/HotTakes.git
cd HotTakes
```

### 2. Backend Setup

Create virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r backend/requirements.txt
```

Configure environment:

```powershell
Copy-Item backend/.env.example backend/.env
# No credentials required — HotTakes uses the public Hacker News Firebase API.
# Edit backend/.env to adjust DATABASE_URL or scheduler settings if needed.
# Startup validates required env vars and constraints. If invalid, the app exits with a clear error message.
```

Initialize database (SQLite for dev):

```text
Database tables are auto-created on first run via SQLAlchemy metadata.
```

Run backend:

```powershell
cd backend
uvicorn app.main:app --reload
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 3. Frontend Setup

In a new terminal:

```powershell
cd frontend
npm install
npm run dev
# Frontend: http://localhost:5173
```

---

## Full Stack with Docker

Requires Docker & Docker Compose.

```powershell
# No credentials required — HotTakes uses the public Hacker News Firebase API
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f backend
```

Access:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- API Docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

Stop services:

```powershell
docker-compose down
```

---

## Environment Variables

Create `backend/.env`:

```env
ENVIRONMENT=development
DATABASE_URL=sqlite:///./social_debate.db

# Hacker News API — no credentials required
MIN_COMMENTS_THRESHOLD=50
HN_MAX_DEPTH=3

SCHEDULER_ENABLED=true
FETCH_INTERVAL_MINUTES=30
```

Full list: see `backend/.env.example`

Validation rules enforced at startup:

- `DATABASE_URL` is required and must include a valid scheme (`postgresql://`, `postgres://`, `sqlite:///`).
- `FETCH_INTERVAL_MINUTES` must be greater than `0`.
- `MAX_COMMENTS_PER_TOPIC` must be greater than or equal to `MAX_COMMENTS_PER_FETCH`.
- `MIN_CLUSTER_SIZE` must be greater than or equal to `2`.
- `ENVIRONMENT` must be one of `development`, `production`, `test`.
- `LOG_LEVEL` must be one of `debug`, `info`, `warning`, `error`, `critical`.

Note:
- Do not commit `.env` files. Keep secrets local; only commit `.env.example`.

---

## Project Structure

```text
HotTakes/
  backend/
    app/
      main.py
      config.py
      database.py
      models.py
      routes/
      services/
      schemas/
      tasks/
    requirements.txt
    .env.example
    Dockerfile
  frontend/
  docker-compose.yml
  PROJECT_SPECIFICATION.md
```

---

## API Endpoints

Swagger UI: `http://localhost:8000/docs`

- `GET /health` - Health check
- `GET /api/topics` - List all topics
- `POST /api/topics` - Create new topic
- `GET /api/comments?topic_id=1` - Get comments
- `GET /api/clusters?topic_id=1` - Get argument clusters
- `GET /api/timeline?topic_id=1` - Get timeline data

---

## Testing

Backend:

```powershell
cd backend
pytest tests/
```

Frontend:

```powershell
cd frontend
npm run test
```

Pre-commit (format + lint):

```powershell
pip install pre-commit black ruff
python -m pre_commit install
python -m pre_commit run --all-files
```

---

## Troubleshooting

Database error "no such table":

- Delete local SQLite DB file and restart API.

HN API returns unexpected data:

- The HN Firebase API is public and requires no credentials.
- Check `MIN_COMMENTS_THRESHOLD` and `HN_MAX_DEPTH` in `backend/.env`.
- Inspect ingestion logs: `docker-compose logs -f backend`

Frontend cannot connect to API:

- Check backend health: `http://localhost:8000/health`
- Verify CORS in `backend/app/config.py`

Port already in use:

- Backend: `uvicorn app.main:app --port 8001`
- Frontend: adjust Vite port in frontend config

---

## Next Steps

1. Implement HN ingestion service (`backend/app/services/hn_ingestion.py`)
2. Implement classification (`backend/app/services/classifier.py`)
3. Implement clustering + analytics
4. Build frontend dashboard
5. Deploy to production

See `PROJECT_SPECIFICATION.md` for full implementation details.

---

## License

MIT
