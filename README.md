# HotTakes

HotTakes is a real-time debate analysis app for Reddit discussions. It ingests comments, classifies stance/sentiment/toxicity, clusters similar arguments, and serves analytics through a FastAPI backend.

## What This Repo Contains

- `backend/`: FastAPI API, database models, routes, scheduler, config
- `frontend/`: frontend workspace scaffold
- `docs/`: additional documentation (optional expansion)
- Root docs: planning/specification and setup guides

## Current Backend Structure

```text
backend/
  app/
    main.py
    config.py
    database.py
    models.py
    routes/
      health.py
      topics.py
      comments.py
      clusters.py
      timeline.py
    tasks/
      scheduler.py
    services/
    schemas/
  tests/
  requirements.txt
  .env.example
  Dockerfile
```

## Quick Start (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
cd backend
uvicorn app.main:app --reload
```

API docs: `http://localhost:8000/docs`

## Docker

```powershell
docker-compose up --build
```

## Key Endpoints

- `GET /health`
- `GET /api/topics`
- `POST /api/topics`
- `GET /api/comments?topic_id=1`
- `GET /api/clusters?topic_id=1`
- `GET /api/timeline?topic_id=1`

## MVP Scope (Locked)

- Platform ingestion: Reddit only (schema remains platform-ready for later expansion)
- Subreddit: `r/soccer`
- Topic focus: player performances + transfers
- Lookback window: last 30 days
- Target volume: 80-200 posts and 8,000-30,000 comments
- Ingestion cadence: every 30 minutes

### Post Filtering (Case-Insensitive)

- Transfer signals: transfer, transfers, here we go, hwg, signed, signing, joins, loan, on loan, fee, release clause, contract, wages, bid, offer, agreement, medical, rumour, rumor, reported, linked, interest, deal, announcement, confirmed, official
- Performance/decision signals: motm, man of the match, performance, form, bottled, carry job, tactics, system, lineup, selection, subs, manager, coach, sacked
- Optional targeting rule: include posts when `(player name + transfer keyword)` is present

### Classification Policy (MVP)

- Stance classes: `SUPPORT`, `OPPOSE`, `MIXED`, `NEUTRAL`
- Single-label record only (no per-aspect split in MVP)
- Stance target is tied to post intent:
- Transfer post: do users approve/disapprove of the transfer?
- Performance/manager post: do users agree/disagree with the take?
- If a comment does not reference target entities, classify as `NEUTRAL` by rule
- Sentiment: `POSITIVE`, `NEUTRAL`, `NEGATIVE`
- Toxicity: score `0.0-1.0` (optionally rendered as low/medium/high in UI)

### Clustering Policy (MVP)

- Similarity = semantic similarity (embeddings + cosine distance), not keyword-only grouping
- Cluster within stance buckets (`SUPPORT` with `SUPPORT`, etc.)
- Target cluster count: 8-12 per stance bucket
- UI should display largest 5-10 clusters overall
- Per cluster output: 5-10 keywords, 1 representative quote, up to 3 top quotes

### Data Limits and Privacy

- Database: PostgreSQL for MVP (local first, cloud after pipeline is stable)
- Keep at most 6 months data; collect last 1 month for MVP
- Soft caps:
- Max comments per topic: 25,000
- Max comments per post: 1,000
- Max comments per ingest cycle: 2,000
- Privacy: store `author_hash`, not raw username
- Removed/deleted comment bodies: skip content, keep metadata

### Quality Gates

- Hide clusters with fewer than 8 comments
- Hide weak clusters where top quotes fail minimum length threshold (40 chars)
- If total classified comments < 300 for a topic, show "not enough data yet" and skip clustering view

### MVP UI Priorities

- Top arguments (cluster summaries + quotes)
- Timeline (stance percentage over time)
- Toxicity trend and toxicity-by-stance
- Optional extra: word clouds
- Deferred to v2: multi-subreddit heatmaps, reply-chain network graphs, websockets/live push

## Starter Bootstrap Script

Use `STARTER_BOOTSTRAP.ps1` to generate missing MVP starter files (service/task stubs, MVP scope constants, and env template) in a fresh clone.

```powershell
powershell -ExecutionPolicy Bypass -File .\STARTER_BOOTSTRAP.ps1
```

## Documentation

- `SETUP_README.md`: detailed setup and troubleshooting
- `PROJECT_SPECIFICATION.md`: full project scope and implementation plan
- `PHASE_0_CHECKLIST.md`: execution checklist

## Status

MVP scaffold is in place; data pipeline, classifier, clustering services, and frontend implementation are the next build phases.
