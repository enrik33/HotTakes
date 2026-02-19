# Project File Structure & Organization Guide

This document shows exactly where every file goes and what it does.

---

## Complete Directory Tree

```
social-debate-analyzer/
│
├── README.md                          ← Start here (project overview)
├── PROJECT_SPECIFICATION.md           ← Full spec (100+ pages)
├── SETUP_README.md                    ← Setup & deployment guide
├── FILES_SUMMARY.md                   ← File organization reference
├── PHASE_0_CHECKLIST.md               ← Day 0 setup tasks
├── FILE_STRUCTURE.md                  ← This file
│
├── .gitignore                         ← Git exclusions (create yourself)
├── docker-compose.yml                 ← Local dev stack
│
├── backend/
│   ├── Dockerfile                     ← Backend container image
│   ├── requirements.txt               ← Python dependencies
│   ├── .env.example                   ← Environment template
│   ├── .env                           ← Local config (create from .env.example)
│   │
│   ├── app/
│   │   ├── __init__.py               ← (create empty file)
│   │   ├── main.py                   ← FastAPI app entry point
│   │   ├── config.py                 ← Settings & env vars
│   │   ├── database.py               ← SQLAlchemy setup
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py           ← (create empty file)
│   │   │   ├── topic.py              ← Topic model (in main models.py)
│   │   │   ├── post.py               ← Post model (in main models.py)
│   │   │   ├── comment.py            ← Comment model (in main models.py)
│   │   │   ├── classification.py     ← Classification model (in main models.py)
│   │   │   ├── embedding.py          ← Embedding model (in main models.py)
│   │   │   └── cluster.py            ← Cluster model (in main models.py)
│   │   │   └── (All above in single models.py file)
│   │   │
│   │   ├── schemas/
│   │   │   ├── __init__.py           ← (create empty file)
│   │   │   ├── topic_schema.py       ← Pydantic models (to implement)
│   │   │   ├── comment_schema.py     ← Comment schemas (to implement)
│   │   │   └── cluster_schema.py     ← Cluster schemas (to implement)
│   │   │
│   │   ├── routes/
│   │   │   ├── __init__.py           ← (create empty file)
│   │   │   ├── health.py             ← GET /health
│   │   │   ├── topics.py             ← GET/POST /api/topics
│   │   │   ├── comments.py           ← GET /api/comments
│   │   │   ├── clusters.py           ← GET /api/clusters
│   │   │   └── timeline.py           ← GET /api/timeline
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py           ← (create empty file)
│   │   │   ├── reddit_fetcher.py     ← PRAW integration (to implement)
│   │   │   ├── classifier.py         ← Classification service (to implement)
│   │   │   ├── embedder.py           ← Embeddings (to implement)
│   │   │   ├── clusterer.py          ← Clustering (to implement)
│   │   │   ├── analytics.py          ← Stats & timeline (to implement)
│   │   │   └── storage.py            ← DB helpers (to implement)
│   │   │
│   │   └── tasks/
│   │       ├── __init__.py           ← (create empty file)
│   │       ├── scheduler.py          ← APScheduler setup
│   │       ├── fetch_job.py          ← Periodic fetch (to implement)
│   │       ├── classify_job.py       ← Periodic classification (to implement)
│   │       └── cluster_job.py        ← Periodic clustering (to implement)
│   │
│   ├── tests/
│   │   ├── __init__.py               ← (create empty file)
│   │   ├── test_classifier.py        ← Tests (to implement)
│   │   ├── test_embedder.py          ← Tests (to implement)
│   │   ├── test_reddit_fetcher.py    ← Tests (to implement)
│   │   └── conftest.py               ← Pytest fixtures (to implement)
│   │
│   └── migrations/
│       └── (Alembic migrations if using - optional for MVP)
│
├── frontend/
│   ├── package.json                  ← React dependencies (to create)
│   ├── vite.config.ts                ← Vite config (to create)
│   ├── tsconfig.json                 ← TypeScript config (to create)
│   ├── tailwind.config.js            ← Tailwind config (to create)
│   ├── postcss.config.js             ← PostCSS config (to create)
│   ├── .env                          ← Frontend env (to create)
│   │
│   ├── public/
│   │   └── (Static assets)
│   │
│   ├── src/
│   │   ├── main.tsx                  ← React entry point
│   │   ├── App.tsx                   ← Main component
│   │   ├── index.css                 ← Global styles
│   │   │
│   │   ├── components/
│   │   │   ├── Dashboard.tsx         ← Main dashboard layout
│   │   │   ├── TimelineChart.tsx     ← Timeline chart
│   │   │   ├── StanceChart.tsx       ← Stance distribution
│   │   │   ├── ClusterView.tsx       ← Clusters display
│   │   │   ├── TopArguments.tsx      ← Top clusters + quotes
│   │   │   ├── CommentList.tsx       ← Paginated comments
│   │   │   ├── ToxicityHeatmap.tsx   ← Toxicity visualization
│   │   │   └── Filters.tsx           ← Filter controls
│   │   │
│   │   ├── pages/
│   │   │   ├── Homepage.tsx          ← Topic explorer
│   │   │   ├── TopicPage.tsx         ← Topic dashboard
│   │   │   └── AdminPage.tsx         ← Admin panel (optional)
│   │   │
│   │   ├── hooks/
│   │   │   ├── useTopics.ts          ← Hook for topics API
│   │   │   ├── useClusters.ts        ← Hook for clusters API
│   │   │   ├── useComments.ts        ← Hook for comments API
│   │   │   └── useTimeline.ts        ← Hook for timeline API
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts             ← Axios instance
│   │   │   ├── topics.ts             ← Topics API
│   │   │   ├── comments.ts           ← Comments API
│   │   │   ├── clusters.ts           ← Clusters API
│   │   │   └── timeline.ts           ← Timeline API
│   │   │
│   │   ├── types/
│   │   │   ├── index.ts              ← TypeScript types
│   │   │   ├── topic.ts              ← Topic types
│   │   │   ├── comment.ts            ← Comment types
│   │   │   └── cluster.ts            ← Cluster types
│   │   │
│   │   └── utils/
│   │       ├── format.ts             ← Formatting helpers
│   │       └── colors.ts             ← Color schemes
│   │
│   └── dist/                         ← Build output (generated)
│
└── docs/
    ├── PROJECT_SPECIFICATION.md      ← (Copy from root)
    ├── API_EXAMPLES.md               ← API request/response examples
    ├── DATABASE.md                   ← Database schema detailed
    └── DEPLOYMENT.md                 ← Deployment walkthrough
```

---

## File Copy Reference

### For this starter pack, here's what to copy where:

**Files provided in this pack:**

| Source File | Destination | Notes |
|------------|-------------|-------|
| `app_main.py` | `backend/app/main.py` | FastAPI entry |
| `app_config.py` | `backend/app/config.py` | Settings |
| `app_database.py` | `backend/app/database.py` | DB setup |
| `app_models.py` | `backend/app/models.py` | ORM models (7 models in 1 file) |
| `routes_health.py` | `backend/app/routes/health.py` | Health check |
| `routes_topics.py` | `backend/app/routes/topics.py` | Topic endpoints |
| `routes_comments.py` | `backend/app/routes/comments.py` | Comment endpoints |
| `routes_clusters.py` | `backend/app/routes/clusters.py` | Cluster endpoints |
| `routes_timeline.py` | `backend/app/routes/timeline.py` | Timeline endpoints |
| `tasks_scheduler.py` | `backend/app/tasks/scheduler.py` | Scheduler |
| `requirements.txt` | `backend/requirements.txt` | Dependencies |
| `.env.example` | `backend/.env.example` | Env template |
| `docker-compose.yml` | `./docker-compose.yml` | Docker stack |
| `Dockerfile` | `./backend/Dockerfile` | Backend image |

**Files you need to create (empty):**

```
backend/app/__init__.py
backend/app/models/__init__.py
backend/app/routes/__init__.py
backend/app/schemas/__init__.py
backend/app/services/__init__.py
backend/app/tasks/__init__.py
backend/tests/__init__.py
frontend/src/__init__.py (if using)
```

---

## Naming Conventions

### Backend

- **Models:** `snake_case.py` (e.g., `reddit_fetcher.py`)
- **Classes:** `PascalCase` (e.g., `class RedditFetcher:`)
- **Functions:** `snake_case` (e.g., `def fetch_posts()`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES = 3`)

### Frontend

- **Components:** `PascalCase.tsx` (e.g., `Dashboard.tsx`)
- **Pages:** `PascalCase.tsx` (e.g., `TopicPage.tsx`)
- **Hooks:** `usePascalCase.ts` (e.g., `useTopics.ts`)
- **Utils:** `snake_case.ts` (e.g., `format.ts`)
- **Types:** `PascalCase.ts` (e.g., `Topic.ts`)

### Database

- **Tables:** `snake_case` (e.g., `daily_stats`)
- **Columns:** `snake_case` (e.g., `created_utc`)
- **Constraints:** `fk_table_column`, `idx_table_column`

---

## What Goes Where: Quick Reference

### Python Backend Files

| Purpose | Location | Examples |
|---------|----------|----------|
| **Models** | `app/models.py` | Topic, Post, Comment, Classification |
| **API Routes** | `app/routes/` | `topics.py`, `comments.py`, etc. |
| **Business Logic** | `app/services/` | `reddit_fetcher.py`, `classifier.py` |
| **Background Jobs** | `app/tasks/` | `fetch_job.py`, `classify_job.py` |
| **Validation** | `app/schemas/` | Pydantic models for request/response |
| **Tests** | `backend/tests/` | `test_classifier.py`, etc. |
| **Config** | `app/config.py` | Settings, env vars |
| **DB** | `app/database.py` | SQLAlchemy setup |

### React Frontend Files

| Purpose | Location | Examples |
|---------|----------|----------|
| **Pages** | `src/pages/` | `TopicPage.tsx`, `Homepage.tsx` |
| **Components** | `src/components/` | `Dashboard.tsx`, `TimelineChart.tsx` |
| **Custom Hooks** | `src/hooks/` | `useTopics.ts`, `useClusters.ts` |
| **API Clients** | `src/api/` | `topics.ts`, `comments.ts` |
| **Types** | `src/types/` | `topic.ts`, `comment.ts` |
| **Utilities** | `src/utils/` | `format.ts`, `colors.ts` |
| **Styles** | `src/` | `index.css`, Tailwind config |

### Config & Infrastructure

| Purpose | Location | Examples |
|---------|----------|----------|
| **Backend Config** | `backend/` | `.env.example`, `requirements.txt` |
| **Docker** | Root | `docker-compose.yml`, `Dockerfile` |
| **Frontend Config** | `frontend/` | `package.json`, `vite.config.ts` |
| **Documentation** | Root | `README.md`, `PROJECT_SPECIFICATION.md` |
| **Database** | Root | SQL schema in spec |

---

## Import Paths Reference

### Backend

```python
# From main.py
from app.config import settings
from app.database import engine, Base, get_db
from app.models import Topic, Post, Comment

# In routes
from app.database import get_db
from app.models import Comment
from sqlalchemy.orm import Session

# In services
from app.database import SessionLocal
from app.models import Topic, Comment

# In tasks
from app.database import SessionLocal
from app.services import classifier, embedder
```

### Frontend

```typescript
// Import components
import Dashboard from '@/components/Dashboard'
import { TimelineChart } from '@/components/TimelineChart'

// Import hooks
import { useTopics } from '@/hooks/useTopics'
import { useClusters } from '@/hooks/useClusters'

// Import API
import { getComments, getClusters } from '@/api'

// Import types
import { Topic, Comment, Cluster } from '@/types'
```

---

## Common Operations

### Add a new route

1. Create file in `app/routes/my_feature.py`
2. In `app/main.py`: `app.include_router(my_feature.router, prefix="/api", tags=["my_feature"])`

### Add a new service

1. Create file in `app/services/my_service.py`
2. Import in required routes: `from app.services import my_service`
3. Use the functions

### Add a background job

1. Create file in `app/tasks/my_job.py`
2. In `app/tasks/scheduler.py`: add to `start_scheduler()`

### Add a React component

1. Create file in `src/components/MyComponent.tsx`
2. Export: `export function MyComponent() { ... }`
3. Import in other components: `import { MyComponent } from '@/components/MyComponent'`

---

## File Size Reference (Approximate)

| File | Size | Status |
|------|------|--------|
| ProjectMVP.md | 100 KB | Complete |
| Backend Code (provided) | 25 KB | Ready |
| Frontend Code (to implement) | ~100 KB | Stub |
| Database | <50 MB (for 25k comments) | Auto-created |
| Models trained | ~500 MB | Downloads on first run |
| Total repo (with node_modules) | ~2 GB | Expect large |

---

## Checklist for Setup

- [ ] Created `backend/app/__init__.py`
- [ ] Created `backend/app/models/__init__.py`
- [ ] Created `backend/app/routes/__init__.py`
- [ ] Created `backend/app/services/__init__.py`
- [ ] Created `backend/app/tasks/__init__.py`
- [ ] Copied `app_main.py` → `backend/app/main.py`
- [ ] Copied `app_config.py` → `backend/app/config.py`
- [ ] Copied `app_database.py` → `backend/app/database.py`
- [ ] Copied `app_models.py` → `backend/app/models.py`
- [ ] Copied all `routes_*.py` → `backend/app/routes/`
- [ ] Copied `tasks_scheduler.py` → `backend/app/tasks/scheduler.py`
- [ ] Copied `.env.example` → `backend/.env.example`
- [ ] Copied `requirements.txt` → `backend/requirements.txt`
- [ ] Copied `docker-compose.yml` → `./docker-compose.yml`
- [ ] Copied `Dockerfile` → `./backend/Dockerfile`
- [ ] Created `.env` from `.env.example` with Reddit credentials
- [ ] All docs copied to root or `/docs`

---

**Quick Start:** Run `PHASE_0_CHECKLIST.md` to set up all folders and files.

**Status:** File structure defined  
**Next:** Follow PHASE_0_CHECKLIST.md
