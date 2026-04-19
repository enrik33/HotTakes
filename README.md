# HotTakes — Project Specification v2.0
### Real-Time Tech Discourse Analyser — Platform Migration & Build Plan

| Field | Value |
|---|---|
| **Author** | Enrik Tsipa |
| **Version** | 2.0.0 |
| **Date** | April 2026 |
| **Status** | In Planning |
| **Repository** | github.com/enrik33/HotTakes |

---

## 01 — Executive Summary

HotTakes is a full-stack debate analytics platform that ingests discussion threads from public forums, classifies each comment by argumentative stance, emotional sentiment, and toxicity level, then groups semantically similar arguments into clusters and exposes the results through a live analytics dashboard.

Version 1.0 was designed around the Reddit API targeting `r/soccer`. Development stalled when Reddit revoked third-party API access under its 2024 developer policy changes, making ingestion legally and technically blocked.

> **Blocking Issue — v1.0**
> Reddit's API policy change blocked all third-party programmatic access to public post and comment data without an approved enterprise agreement. The ingestion layer — the foundation of the entire pipeline — could not be built.

This document specifies the **v2.0 migration**: replacing Reddit with the **Hacker News Firebase API** as the data source, while preserving the entire backend architecture, data model, classification pipeline, and clustering logic already designed. The product scope shifts from football discourse to **technology discourse** — a better fit for the developer audience evaluating this project, and a stronger signal for job applications in the tech industry.

> **Strategic Value**
> Hacker News is free, open, requires no authentication, has no rate-limit restrictions on its public API, and its audience — professional software engineers — is exactly the same audience that will read this project on a CV or in a job interview.

---

## 02 — Data Source Migration: Reddit → Hacker News

The following comparison documents the technical and strategic rationale for the migration.

| | Reddit API ❌ | Hacker News API ✅ |
|---|---|---|
| **Endpoint** | oauth.reddit.com | hacker-news.firebaseio.com/v0 |
| **Auth required** | Yes — OAuth 2.0 | None |
| **Access policy** | Restricted (2024) | Fully open / Firebase |
| **Rate limit** | 60 req/min (approved) | None documented |
| **Cost** | Paid above threshold | Free |
| **Legal risk** | High (ToS breach) | None |
| **Audience** | r/soccer: football fans | Senior engineers, founders |

The HN API exposes five primary endpoints relevant to this project: `topstories`, `newstories`, `askstories`, `showstories`, and individual item detail. Each comment (called a "kid") is a separate item with its own ID and parent reference, matching the threading model the v1.0 schema was already designed to support.

> **Scope Shift**
> The product topic changes from *football transfers and player performances* to *technology opinions and industry debates*. This means "Ask HN", controversial technical posts, and AI/startup discussions replace r/soccer transfer threads. The classification logic (stance, sentiment, toxicity) applies equally well — HN is famously opinionated.

---

## 03 — Current State Audit

| Component | Location | Status | Notes |
|---|---|---|---|
| FastAPI app entrypoint | `backend/app/main.py` | ✅ Built | App initialized, CORS configured, routers registered. Carries over unchanged. |
| Database models | `backend/app/models.py` | ✅ Built | Platform-agnostic schema with `platform` field and `author_hash`. Minimal change needed. |
| Database connection | `backend/app/database.py` | ✅ Built | SQLAlchemy 2.0 async session factory. No changes required. |
| Config / env | `backend/app/config.py` | ⚠️ Update needed | Remove Reddit OAuth credentials. No HN credentials needed — simpler config. |
| API routes | `backend/app/routes/` | ✅ Built | health, topics, comments, clusters, timeline all scaffolded. Carries over. |
| Scheduler | `backend/app/tasks/scheduler.py` | ⚠️ Stub only | APScheduler initialized. Ingestion job to be wired in Phase 2. |
| Ingestion service | `backend/app/services/` | ❌ Not built | Reddit fetcher was never implemented. New HN fetcher to be built in Phase 2. |
| Classification service | `backend/app/services/` | ❌ Not built | Stance, sentiment, toxicity classification stubs only. Build in Phase 3. |
| Clustering service | `backend/app/services/` | ❌ Not built | Embedding + cosine similarity clustering. Build in Phase 4. |
| Docker / Compose | `docker-compose.yml` | ✅ Built | PostgreSQL + app services defined. Carries over with minor env updates. |
| Frontend dashboard | *(not created)* | ❌ Not built | React app with stance timeline, cluster view, toxicity charts. Build in Phase 5. |
| Deployment | *(not configured)* | ❌ Not done | Railway for backend, Vercel for frontend. Phase 6. |

---

## 04 — Change Impact Analysis

The migration from Reddit to Hacker News is primarily a **data source swap**. The architecture, tech stack, and pipeline design are preserved in full.

### Removed / Replaced

- **Reddit OAuth credentials** — removed from config entirely. No replacement needed.
- **PRAW / aiohttp Reddit client** — replaced with simple async HTTP calls to HN Firebase API.
- **Subreddit-based post filtering** — replaced with HN story type targeting (Ask HN, Show HN, top stories).
- **Soccer-domain keyword lists** — transfer/performance keywords replaced with tech-domain keywords (AI, layoffs, funding, open source, etc.).
- **r/soccer-specific stance framing** — "approve/disapprove of transfer" replaced with "agree/disagree with the technical take".
- **PROJECT_SPECIFICATION.md v1** — superseded by this document.

### Preserved Unchanged

- **FastAPI application** — entrypoint, CORS, router registration, all routes.
- **SQLAlchemy models** — platform-agnostic schema carries over. The `platform` field simply stores `"hackernews"`.
- **Docker Compose setup** — PostgreSQL + app services unchanged.
- **APScheduler scaffold** — 30-minute ingestion cadence maintained.
- **Classification policy** — stance labels (SUPPORT / OPPOSE / MIXED / NEUTRAL), sentiment, toxicity scoring.
- **Clustering policy** — embedding cosine similarity, 8–12 clusters per stance bucket, quality gates (<8 comments, <40 char quotes).
- **All API route contracts** — `/topics`, `/comments`, `/clusters`, `/timeline` unchanged.
- **Privacy policy** — `author_hash` instead of raw usernames, retained.

---

## 05 — Technology Stack

Items marked `[NEW]` are additions for v2.0. Items marked `[REMOVED]` are eliminated.

### Data Ingestion
`HN Firebase API [NEW]` `aiohttp` `APScheduler` ~~`PRAW (Reddit) [REMOVED]`~~ ~~`OAuth 2.0 [REMOVED]`~~

### Backend API
`FastAPI` `SQLAlchemy 2.0` `Pydantic v2` `Uvicorn`

### Database
`PostgreSQL` `asyncpg` `Alembic`

### NLP / Classification
`sentence-transformers [NEW]` `Detoxify [NEW]` `scikit-learn` `TextBlob`

### Frontend
`React 18` `TypeScript` `TanStack Query` `Recharts` `Tailwind CSS`

### Infra & Deployment
`Docker` `Docker Compose` `Railway [NEW]` `Vercel [NEW]` `GitHub Actions [NEW]`

---

## 06 — Implementation Plan

### Phase 01 — Repository Cleanup & Data Source Wiring
**Duration:** ~2 days

**Tasks:**
- Delete all Reddit-related code, credentials, and config references from the codebase
- Update `.env.example` — remove Reddit OAuth vars, no HN credentials needed
- Write and test a minimal **HN API client** — fetch top stories, item detail, and child comments by ID
- Verify comment tree traversal (HN nests comments as "kids" arrays recursively)
- Update `PROJECT_SPECIFICATION.md` — archive v1.0, link this document as v2.0
- Update `README.md` with new product description and quick-start instructions
- Confirm Docker + PostgreSQL stack starts cleanly locally

**Key Decisions:**
- **Story types to target:** "Ask HN" threads, "Show HN" posts, and top stories with ≥50 comments
- **Keyword filter approach:** title-based keyword matching on ingestion, same pattern as v1.0 soccer keywords
- **Comment depth limit:** fetch max 3 levels of reply nesting to control volume

**Deliverable:** Docker Compose starts, HN API client fetches a real story and its comments successfully, no Reddit references remain in the codebase, documentation updated.

---

### Phase 02 — Ingestion Pipeline
**Duration:** ~4 days

**Tasks:**
- Implement **HNIngestionService** — fetches top/ask/show story IDs, filters by keyword list and comment count threshold
- Implement **comment tree fetcher** — recursively resolves kid IDs to comment objects, respects depth limit
- Implement **database writer** — upserts stories as Topics, comments as Comments; deduplication by external HN item ID
- Apply **author privacy** — hash HN usernames with SHA-256 before storage, never store raw
- Wire the ingestion service into the **APScheduler job** at 30-minute interval
- Add **volume caps**: max 25,000 comments per topic, max 1,000 per story, max 2,000 per fetch cycle
- Write **integration tests** against the live HN API using real story IDs

**Tech-Domain Keyword List:**
- **AI/ML:** LLM, GPT, Claude, Gemini, AI, machine learning, neural, model
- **Industry:** layoffs, funding, acquisition, IPO, startup, valuation, fired
- **Open source:** open source, license, fork, maintainer, abandoned
- **Engineering:** performance, scaling, rewrite, architecture, security breach, outage
- **Opinion triggers:** "Ask HN: should we…", "Is X dead?", "Why does X suck?"

**Deliverable:** Scheduler runs every 30 minutes. After one cycle, database contains real HN stories and comments. Volume caps enforced. Author usernames are hashed. Confirmed via `GET /api/topics` returning live data.

---

### Phase 03 — Classification Pipeline
**Duration:** ~5 days

**Tasks:**
- Implement **StanceClassifier** — zero-shot classification using a sentence-transformers model (e.g. `cross-encoder/nli-deberta-v3-small`) against topic-derived hypothesis pairs
- Implement **SentimentClassifier** — TextBlob or HuggingFace distilbert-sentiment for POSITIVE / NEUTRAL / NEGATIVE labels
- Implement **ToxicityScorer** — Detoxify library returns a 0.0–1.0 float score per comment
- Build **ClassificationService** that runs all three in sequence per comment, writes results back to the comments table
- Wire classification as a **post-ingestion step** — triggered after each ingestion cycle, processes only unclassified comments
- Build a **manual labelling script** for at least 200 comments — output CSV used to validate model accuracy before deployment
- Define quality gate: skip clustering if fewer than 300 classified comments exist for a topic

**Stance Logic for HN:**
- For **opinion/ask threads:** stance relative to the parent post's position (agree vs. disagree with the take)
- For **news threads:** stance relative to the entity or event (support vs. oppose the layoff, acquisition, etc.)
- Comments that don't reference the thread subject → auto-label **NEUTRAL**
- Short comments under 15 words → classify but flag as low-confidence

**Deliverable:** Every comment in the database has a stance, sentiment, and toxicity score. `GET /api/comments?topic_id=X` returns classification fields. Manual validation shows ≥70% stance accuracy on labeled sample.

---

### Phase 04 — Clustering & Analytics Aggregation
**Duration:** ~4 days

**Tasks:**
- Implement **EmbeddingService** — generate sentence embeddings using `all-MiniLM-L6-v2`, store as a float array column in PostgreSQL
- Implement **ClusteringService** — KMeans on cosine-normalized embeddings, grouped within stance buckets; target 8–12 clusters per bucket
- Per cluster: extract **5–10 keywords** (TF-IDF within cluster), select **1 representative quote** (centroid-nearest comment), surface **top 3 quotes** by upvote score
- Implement **quality gates**: suppress clusters with fewer than 8 comments; drop quotes under 40 characters
- Build **timeline aggregation query**: stance percentage breakdown per 6-hour bucket over last 30 days
- Build **toxicity aggregation query**: average toxicity score by stance label and by time window
- Wire cluster and timeline data into existing `/api/clusters` and `/api/timeline` routes

**Output per Cluster:**
- `cluster_id`, `stance_label`, `comment_count`
- `keywords[]` — top 5–10 descriptive phrases
- `representative_quote` — closest comment to cluster centroid
- `top_quotes[]` — up to 3 highest-score comments in cluster
- `avg_toxicity`, `avg_sentiment` — numeric aggregates

**Deliverable:** `GET /api/clusters?topic_id=X` returns grouped argument clusters with keywords and quotes. `GET /api/timeline?topic_id=X` returns stance percentages over time. All quality gates enforced.

---

### Phase 05 — Frontend Dashboard
**Duration:** ~6 days

**Views & Components:**
- **Topic List** — browse ingested HN threads, sorted by activity; search by keyword
- **Topic Detail — Argument Clusters** — tabbed by stance (SUPPORT / OPPOSE / MIXED); each cluster shows keywords, representative quote, and top comments
- **Stance Timeline Chart** — stacked area or line chart of stance percentages over time using Recharts
- **Toxicity Dashboard** — toxicity trend line + toxicity-by-stance breakdown
- **Comment Explorer** — filterable table of comments with stance, sentiment, toxicity columns
- **Not Enough Data** — graceful empty state when classified comments < 300

**Technical Requirements:**
- React 18 + TypeScript, Tailwind CSS for styling
- TanStack Query for all data fetching with 5-minute polling interval
- React Router for topic list → detail navigation
- Fully **responsive** — desktop and mobile layouts
- Loading skeletons and error boundaries on all data-fetching components
- No authentication required — read-only public dashboard

**Deliverable:** React app running locally, consuming live backend data. All five views functional. Responsive on mobile. No console errors. Connected to the deployed backend URL.

---

### Phase 06 — Deployment & Public Launch
**Duration:** ~2 days

**Tasks:**
- Deploy **PostgreSQL + FastAPI backend** to Railway — configure environment variables, health check endpoint, persistent volume for DB
- Deploy **React frontend** to Vercel — set API base URL env var pointing to Railway backend
- Set up **GitHub Actions CI** — run backend tests on every push to main; block merge on failure
- Configure **automatic deployment** — Railway deploys on push to main; Vercel deploys on push to main
- Seed the database with **≥3 real HN threads** with sufficient comment volume to demonstrate clustering
- Update **README** with live URL, architecture diagram, and 3–4 dashboard screenshots
- Add **live demo link** to GitHub repository description

**Deployment Targets:**
- **Backend:** Railway free tier — FastAPI + PostgreSQL, persistent, always-on
- **Frontend:** Vercel — automatic HTTPS, global CDN, preview deployments per PR
- **CI:** GitHub Actions — pytest on backend, TypeScript type-check on frontend
- **Monitoring:** Railway logs + FastAPI `/health` endpoint returning uptime and last ingestion timestamp

**Deliverable:** Live public URL accessible to anyone. Backend scheduler running in production. Frontend showing real HN data. README has screenshots and architecture overview. GitHub repo description has the live link.

---

## 07 — Definition of Done

The project is considered complete when every criterion below is verifiable by a third party visiting the public URL with no setup required.

- [ ] **Live URL exists.** The application is publicly accessible at a stable URL with no login required.
- [ ] **Real data is visible.** At least 3 HN threads are fully ingested with classified comments and rendered clusters.
- [ ] **Clustering works end-to-end.** Each topic shows at least 2 populated stance clusters with keywords and representative quotes.
- [ ] **Timeline chart is populated.** Stance percentage over time is visible and updates with new ingestion cycles.
- [ ] **Scheduler is running in production.** The `/health` endpoint returns a last-ingestion timestamp updated within the last hour.
- [ ] **CI passes.** GitHub Actions green on main. Backend tests and frontend type-check both pass.
- [ ] **README is complete.** Live URL, architecture diagram, and screenshots are present. Any developer can run it locally in under 10 minutes.
- [ ] **Privacy is enforced.** No raw HN usernames are stored anywhere in the database. `author_hash` only.

---

*HotTakes v2.0 — Project Specification — Enrik Tsipa — April 2026 — github.com/enrik33/HotTakes*
