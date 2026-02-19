# Social Debate Analyzer - Project Files Summary

## Overview

This is a complete copy-paste-ready starter pack for the Social Debate Analyzer project. All files are listed below with their purposes.

---

## Core Documentation

1. **PROJECT_SPECIFICATION.md** — Complete project specification with:
   - Full project overview and MVP scope
   - Data collection strategy (keywords, filtering, APIs)
   - Classification system (stance, sentiment, toxicity)
   - Database schema with SQL
   - Architecture & tech stack
   - API specification (all endpoints)
   - Frontend requirements
   - 6-phase implementation plan (2–3 weeks)
   - Quality gates & validation
   - Deployment instructions
   - Troubleshooting guide

2. **SETUP_README.md** — Local setup & deployment guide:
   - Prerequisites
   - Quick start (backend + frontend)
   - Docker setup
   - Environment variables
   - API endpoints overview
   - Testing
   - Troubleshooting
   - Deployment to Railway

---

## Backend Files

### Core Application

3. **app/main.py** — FastAPI application entry point
   - Initializes FastAPI app
   - CORS middleware setup
   - Route registration
   - Startup/shutdown lifecycle

4. **app/config.py** — Configuration and settings
   - Loads environment variables
   - Settings for database, Reddit, scheduler, ML models
   - Uses Pydantic BaseSettings

5. **app/database.py** — Database connection setup
   - SQLAlchemy engine creation
   - Session factory
   - Dependency injection for DB

6. **app/models.py** — SQLAlchemy ORM models
   - Topic (debate subjects)
   - Post (Reddit posts)
   - Comment (Reddit comments)
   - Classification (stance/sentiment/toxicity)
   - Embedding (vector embeddings)
   - Cluster (argument groups)
   - DailyStats (timeline data)

### API Routes

7. **routes/health.py** — Health check endpoint
   - GET /health — Status check with uptime, DB connection

8. **routes/topics.py** — Topics CRUD endpoints
   - GET /api/topics — List all topics
   - POST /api/topics — Create new topic
   - GET /api/topics/{id} — Get topic details + stats

9. **routes/comments.py** — Comments listing endpoint
   - GET /api/comments — Filterable, paginated comment list
   - Filters: stance, sentiment, toxicity
   - Sorting: newest, scored, most_relevant

10. **routes/clusters.py** — Argument clusters endpoint
    - GET /api/clusters — Get clusters by topic + stance
    - Returns keywords, representative quote, top quotes

11. **routes/timeline.py** — Timeline/stats endpoint
    - GET /api/timeline — Daily stance breakdown
    - Returns stance percentages + toxicity trend

### Services & Tasks (Stubs)

12. **tasks/scheduler.py** — Background job scheduler
    - APScheduler setup
    - Job stubs: fetch_reddit_data, classify_comments, cluster_arguments, compute_daily_stats

### To Be Implemented

- `services/reddit_fetcher.py` — PRAW integration, data fetching
- `services/classifier.py` — Stance/sentiment/toxicity classification
- `services/embedder.py` — Sentence-transformers wrapper
- `services/clusterer.py` — KMeans clustering + label extraction
- `services/analytics.py` — Timeline/stats computation
- `tasks/fetch_job.py` — Periodic fetch job
- `tasks/classify_job.py` — Periodic classification job
- `tasks/cluster_job.py` — Periodic clustering job

---

## Configuration Files

13. **.env.example** — Environment variable template
    - Reddit API credentials
    - Database URL
    - Scheduler settings
    - ML model configs
    - Data limits
    - Copy to `.env` and fill in values

14. **requirements.txt** — Python dependencies
    - FastAPI, SQLAlchemy, PRAW
    - scikit-learn, sentence-transformers, transformers
    - APScheduler, aiohttp
    - Testing: pytest

---

## Docker & Deployment

15. **docker-compose.yml** — Local development stack
    - PostgreSQL service
    - Backend service (FastAPI)
    - Frontend service (Node.js)
    - Auto health checks
    - Volume persistence

16. **Dockerfile** — Backend container image
    - Python 3.11-slim
    - Installs dependencies
    - Exposes port 8000
    - Health check
    - Runs uvicorn

---

## Frontend Files (Structure Only)

The specification includes full frontend requirements in `PROJECT_SPECIFICATION.md`:

### To Be Created

- **frontend/package.json** — React + Vite setup
- **frontend/src/App.tsx** — Main React component
- **frontend/src/components/** — React components:
  - Dashboard.tsx
  - TimelineChart.tsx
  - ClusterView.tsx
  - TopArguments.tsx
  - CommentList.tsx
  - ToxicityHeatmap.tsx
- **frontend/src/pages/** — Pages:
  - TopicPage.tsx
  - ExploreTopics.tsx
- **frontend/src/api/client.ts** — API client
- **frontend/vite.config.ts** — Build config
- **frontend/tailwind.config.js** — Tailwind CSS

---

## How to Use This Pack

### 1. Create Your Repository

```bash
mkdir social-debate-analyzer
cd social-debate-analyzer
git init
```

### 2. Create Directory Structure

```bash
mkdir -p backend/app/{models,routes,services,tasks}
mkdir -p frontend/src/{components,pages,api}
```

### 3. Copy Backend Files

Copy these files into `backend/app/`:
- `app_main.py` → `app/main.py`
- `app_config.py` → `app/config.py`
- `app_database.py` → `app/database.py`
- `app_models.py` → `app/models.py`

Copy these into `backend/app/routes/`:
- `routes_health.py` → `routes/health.py`
- `routes_topics.py` → `routes/topics.py`
- `routes_comments.py` → `routes/comments.py`
- `routes_clusters.py` → `routes/clusters.py`
- `routes_timeline.py` → `routes/timeline.py`

Create `backend/app/routes/__init__.py` (empty)

Copy these into `backend/app/tasks/`:
- `tasks_scheduler.py` → `tasks/scheduler.py`

Create `backend/app/tasks/__init__.py` (empty)

Create `backend/app/models/__init__.py` (empty)
Create `backend/app/schemas/__init__.py` (empty)
Create `backend/app/services/__init__.py` (empty)

### 4. Copy Configuration Files

In `backend/`:
- `requirements.txt`
- `.env.example`

In root:
- `docker-compose.yml`
- `Dockerfile` → `backend/Dockerfile`
- `PROJECT_SPECIFICATION.md`
- `SETUP_README.md` → `README.md` (or keep both)

### 5. Initialize Git

```bash
echo "venv/" > .gitignore
echo ".env" >> .gitignore
echo "*.db" >> .gitignore
echo "__pycache__/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "node_modules/" >> .gitignore
echo ".env.local" >> .gitignore

git add .
git commit -m "Initial project setup"
```

### 6. Follow Setup Guide

See `SETUP_README.md` for:
- Installing dependencies
- Setting up Reddit API credentials
- Running locally
- Running with Docker

---

## What's Already Done

✅ Database schema designed (with SQL)  
✅ API endpoints defined (with request/response specs)  
✅ Bootstrap code for FastAPI, models, routes  
✅ Configuration system set up  
✅ Docker infrastructure ready  
✅ Project documentation complete  
✅ Implementation phases laid out  

## What You Need to Implement

1. **services/reddit_fetcher.py** — Reddit data collection (PRAW)
2. **services/classifier.py** — Stance/sentiment/toxicity classification
3. **services/embedder.py** — Text embedding generation
4. **services/clusterer.py** — Semantic clustering + labeling
5. **services/analytics.py** — Timeline computation
6. **tasks/fetch_job.py** → **classify_job.py** → **cluster_job.py** — Job wrappers
7. **Frontend** — React dashboard (structure in spec)
8. **Tests** — Unit + integration tests
9. **Labeling** — Label 150–250 comments for training classifier

---

## Timeline (Recommended)

| Phase | Days | Goal |
|-------|------|------|
| **0. Setup** | Day 0 | Environment + hello world |
| **1. Data** | Days 1–3 | Fetch 5k–10k Reddit comments |
| **2. Classification** | Days 3–5 | Classify stance/sentiment/toxicity |
| **3. Clustering** | Days 5–7 | Group similar arguments |
| **4. Frontend** | Days 7–10 | React dashboard |
| **5. Deployment** | Days 10–14 | Deploy to Railway |
| **6. Polish** | Days 14–21 | Iterate + improve |

---

## Key Success Metrics (End of MVP)

- ✅ 10k+ comments in database
- ✅ Stance classifier >70% accuracy
- ✅ 5–10 argument clusters per stance
- ✅ Working timeline + toxicity charts
- ✅ Deployed to production
- ✅ Auto-updates every 30 minutes

---

## Support

- All API specs in `PROJECT_SPECIFICATION.md`
- Setup instructions in `SETUP_README.md`
- Troubleshooting section in `PROJECT_SPECIFICATION.md`

---

**Generated:** February 19, 2026  
**Project:** Social Debate Analyzer (Reddit r/soccer)  
**Status:** MVP Specification + Bootstrap Code Ready
