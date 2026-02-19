# HotTakes - Complete Summary

## Delivered in Repository

- Backend FastAPI scaffold in `backend/app`
- SQLAlchemy models in `backend/app/models.py`
- API routes in `backend/app/routes`
- Scheduler scaffold in `backend/app/tasks/scheduler.py`
- Environment template in `backend/.env.example`
- Docker setup (`backend/Dockerfile`, `docker-compose.yml`)
- Starter bootstrap script: `STARTER_BOOTSTRAP.ps1`
- Core docs: `README.md`, `SETUP_README.md`, `PROJECT_SPECIFICATION.md`

## MVP Scope Snapshot

- Subreddit: `r/soccer`
- Topic: transfers + player/manager performance
- Window: last 30 days
- Cadence: 30-minute ingestion
- Class labels: `SUPPORT`, `OPPOSE`, `MIXED`, `NEUTRAL`
- Clustering: semantic similarity within stance buckets

## Immediate Next Work

1. Implement Reddit fetcher (`backend/app/services/reddit_fetcher.py`)
2. Implement classifier (`backend/app/services/classifier.py`)
3. Implement clustering pipeline (`embedder.py`, `clusterer.py`)
4. Add analytics aggregation for timeline + toxicity trend
5. Add tests under `backend/tests`

## Definition of Ready for MVP Demo

- >= 300 classified comments for selected topic
- Valid stance timeline endpoint output
- Cluster endpoint excludes clusters `< 8` comments
- Top arguments includes representative + top quotes
- Dashboard auto-refreshes every 5 minutes
