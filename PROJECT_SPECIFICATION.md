# HotTakes — Project Specification v2.0
### Real-Time Tech Discourse Analyser

| Field | Value |
|---|---|
| **Author** | Enrik Tsipa |
| **Version** | 2.0.0 |
| **Status** | In Progress |
| **Repository** | github.com/enrik33/HotTakes |

---

## 1. Product Goal

HotTakes is a full-stack debate analytics platform that ingests discussion threads from Hacker News, classifies each comment by argumentative stance, emotional sentiment, and toxicity level, then groups semantically similar arguments into clusters and exposes the results through a live analytics dashboard.

v2.0 targets **tech discourse** — AI/ML debates, startup news, engineering opinion threads — replacing the v1.0 r/soccer scope that was blocked by Reddit's 2024 API policy changes.

---

## 2. Data Source

- **Platform:** Hacker News Firebase API (public, no authentication, no rate limits)
- **Base URL:** `https://hacker-news.firebaseio.com/v0/`
- **Story types ingested:** top stories, Ask HN, Show HN
- **Story filter:** title keyword match + minimum 50 comments
- **Comment depth limit:** 3 levels of reply nesting
- **Update interval:** every 30 minutes

Target volume per active topic:

- stories: 50–200
- comments: 5,000–30,000

---

## 3. Tech-Domain Keyword List

**AI/ML:** LLM, GPT, Claude, Gemini, AI, machine learning, neural network, model, fine-tuning, inference, alignment, safety, agent, RAG, transformer

**Industry:** layoffs, funding, acquisition, IPO, startup, valuation, fired, open source, license, fork, maintainer, abandoned

**Engineering:** performance, scaling, rewrite, architecture, security breach, outage

---

## 4. Data Model

Platform-agnostic schema — `platform` field stores `"hackernews"`.

Stored per comment:

- `platform`, `external_id` (HN item ID)
- `created_utc`, `author_hash` (SHA-256 of HN username — no raw usernames stored)
- `parent_comment_id` (null if direct reply to story)
- `body`, `score`

Limits:

- max comments/topic: 25,000
- max comments/story: 1,000
- max comments/fetch cycle: 2,000

---

## 5. Classification

**Stance labels:** `SUPPORT` / `OPPOSE` / `MIXED` / `NEUTRAL`

Policy:

- one comment → one stance label
- comments that do not reference thread subject → auto `NEUTRAL`
- short comments (< 15 words) → classify but flag as low-confidence

**Sentiment labels:** `POSITIVE` / `NEUTRAL` / `NEGATIVE`

**Toxicity:** numeric score `0.0–1.0` (Detoxify library)

---

## 6. Stance Framing for HN

- **Opinion/Ask HN threads:** stance relative to the parent post's position (agree vs. disagree with the take)
- **News threads:** stance relative to the entity or event (support vs. oppose the layoff, acquisition, etc.)

---

## 7. Clustering

- Semantic similarity via `all-MiniLM-L6-v2` embeddings + cosine distance
- KMeans clustered within stance buckets
- Target: 8–12 clusters per stance bucket
- Per cluster: 5–10 keywords (TF-IDF), 1 representative quote (centroid-nearest), top 3 quotes by score

Quality gates:

- suppress clusters with < 8 comments
- drop quotes under 40 characters
- if classified comments < 300, show "not enough data yet" and skip clustering view

---

## 8. API Routes

- `GET /health` — uptime + last ingestion timestamp
- `GET /api/topics` — list ingested HN threads
- `POST /api/topics` — create topic
- `GET /api/comments?topic_id=X` — comments with classification fields
- `GET /api/clusters?topic_id=X` — argument clusters with keywords and quotes
- `GET /api/timeline?topic_id=X` — stance percentages per 6-hour bucket over 30 days

---

## 9. Frontend Views

- **Topic List** — browse ingested threads, sorted by activity; keyword search
- **Argument Clusters** — tabbed by stance; keywords, representative quote, top comments per cluster
- **Stance Timeline** — stacked area/line chart of stance percentages over time
- **Toxicity Dashboard** — toxicity trend + toxicity-by-stance breakdown
- **Comment Explorer** — filterable table with stance, sentiment, toxicity columns

Tech: React 18 + TypeScript, Tailwind CSS, TanStack Query (5-minute polling), Recharts, React Router.

---

## 10. Tech Stack

- **API:** FastAPI + Uvicorn
- **ORM:** SQLAlchemy 2.0
- **DB:** PostgreSQL (asyncpg), Alembic migrations
- **Scheduler:** APScheduler (30-minute ingestion cadence)
- **Async HTTP:** aiohttp (HN Firebase API client)
- **NLP:** sentence-transformers, Detoxify, scikit-learn, TextBlob
- **Frontend:** React 18, TypeScript, Tailwind, TanStack Query, Recharts
- **Infra:** Docker Compose (local), Railway (backend), Vercel (frontend), GitHub Actions (CI)

---

## 11. Implementation Order

1. ✅ Phase 01 — Repository cleanup & HN API client
2. Phase 02 — Ingestion pipeline (HNIngestionService + comment tree fetcher)
3. Phase 03 — Classification pipeline (stance, sentiment, toxicity)
4. Phase 04 — Clustering & analytics aggregation
5. Phase 05 — Frontend dashboard
6. Phase 06 — Deployment (Railway + Vercel) & public launch

---

## 12. Definition of Done

- Live public URL accessible to anyone, no login required
- At least 3 HN threads fully ingested with classified comments and rendered clusters
- Each topic shows ≥2 populated stance clusters with keywords and representative quotes
- Stance timeline chart populated and updating with new ingestion cycles
- `/health` endpoint returns last-ingestion timestamp updated within the last hour
- GitHub Actions CI green on main (backend tests + frontend type-check)
- README has live URL, architecture diagram, and screenshots
- No raw HN usernames stored — `author_hash` only throughout
