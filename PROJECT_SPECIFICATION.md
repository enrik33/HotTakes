# Social Debate Analyzer - Complete Project Specification

**Project:** Real-Time Social Debate Analyzer (r/soccer focus)  
**Status:** MVP Definition  
**Timeline:** 2–3 weeks  
**Start Date:** February 19, 2026

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Data Collection Strategy](#data-collection-strategy)
3. [Classification System](#classification-system)
4. [Database Schema](#database-schema)
5. [Architecture & Tech Stack](#architecture--tech-stack)
6. [API Specification](#api-specification)
7. [Frontend Requirements](#frontend-requirements)
8. [Implementation Phases](#implementation-phases)
9. [Quality Gates & Validation](#quality-gates--validation)
10. [Deployment](#deployment)

---

## Project Overview

### What It Does
Fetches Reddit posts and comments from r/soccer (transfers + performance topics), classifies opinions (SUPPORT/OPPOSE/MIXED/NEUTRAL), detects emotional tone (positive/neutral/negative + toxicity score), clusters similar arguments semantically, and visualizes findings on a dashboard.

### MVP Scope
- **Data source:** r/soccer only (Reddit API)
- **Historical pull:** Last 1 month of posts + comments
- **Update frequency:** Every 30 minutes
- **Target volume:** 80–200 posts, 8,000–30,000 comments
- **Key views:** Top arguments (clustered), timeline (stance %), toxicity trend
- **Infrastructure:** Platform-agnostic database schema (ready for YouTube/Twitter v2)

### Success Criteria (MVP)
- ✅ Successfully fetch, clean, and store 10k+ comments
- ✅ Classify stance with >70% accuracy on test set
- ✅ Generate readable argument clusters (8–12 per stance)
- ✅ Show timeline + toxicity + top arguments on dashboard
- ✅ Runs locally + deployable to Railway

---

## Data Collection Strategy

### Reddit Post Filtering

**Keywords (case-insensitive):**

| Category | Keywords |
|----------|----------|
| **Transfers** | transfer, transfers, here we go, HWG, signed, signing, joins, loan, on loan, fee, release clause, contract, wages, bid, offer, agreement, medical, rumour, rumor, reported, linked, interest, deal, announcement, confirmed, official |
| **Performance/Manager** | motm, man of the match, performance, form, bottled, carry job, tactics, system, lineup, selection, subs, manager, coach, sacked |

**Filtering Logic:**
1. Fetch posts from r/soccer (last 30 days, sticky=False)
2. Filter by keyword match in title OR selftext
3. Optional: name-based targeting (if a player/manager name + transfer keyword appears, include)
4. Store all matching posts with metadata

### Data Ingestion Pipeline

**Update Schedule:** Every 30 minutes via APScheduler

**Per Update Cycle:**
- Max 2,000 new comments ingested
- Fetch comments from all stored posts (sorted by latest first)
- Skip already-stored comments (use external_id deduplication)
- Clean + structure text before storage

**Rate Limiting:**
- Reddit API: respect official rate limits (60 requests/min for authenticated calls)
- Implement exponential backoff on 429 responses
- Cache post metadata to avoid re-fetching

### Data Storage Philosophy

**What to keep:**
- Post ID, title, selftext, author_hash, created_utc, score, permalink, subreddit
- Comment ID, body, author_hash, created_utc, score, parent_comment_id, post_id, parenthesis relationships
- Metadata: fetched_at, platform, external_id

**What to filter out:**
- Deleted/removed comments (skip if `[deleted]` or `[removed]`)
- Extremely short comments (<5 characters)
- Obvious spam/bots (auto-mod posts, common copypasta patterns)

**Data retention:** 6 months max (for MVP, only store 1 month anyway)

**Caps per topic:**
- 25,000 comments max per topic
- 1,000 comments max per post (ingest oldest 1,000 if more exist)

---

## Classification System

### Stance Classification

**4 Classes:**
- **SUPPORT:** Mostly positive toward the target (player/transfer/manager decision)
- **OPPOSE:** Mostly negative
- **MIXED:** Explicitly contains both positive and negative perspectives
- **NEUTRAL:** Factual, jokes, unrelated, or no clear stance

**Rules:**
1. Only classify comments that mention the target (player/club/manager keywords from the post)
2. Everything else = NEUTRAL automatically
3. If comment contains multiple opinions but they're inseparable, mark MIXED
4. One label per comment (no splitting)

**Target Definition:**
- **Transfer post:** Stance = approval of the signing/transfer (support = good move, oppose = bad idea)
- **Performance/Manager post:** Stance = agreement with the take (support = agree with criticism, oppose = disagree/defend)

### Sentiment Classification

**3 Classes:**
- **POSITIVE:** Optimistic, praising, hopeful tone
- **NEUTRAL:** Factual, informational, balanced
- **NEGATIVE:** Critical, pessimistic, complaining tone

**Toxicity Score:** 0.0–1.0 (displayed as Low 0–0.33, Medium 0.33–0.67, High 0.67–1.0)

### Model Strategy

**Phase 1 (Days 1–2):**
- Rule-based filtering: only classify comments with target keywords
- Everything else = NEUTRAL (boosts accuracy dramatically)

**Phase 2 (Days 2–3):**
- Label 150–250 comments manually (balanced across classes)
- Train v1 stance classifier (logistic regression on TF-IDF + embeddings)
- Quick evaluation on held-out test set (aim for >70% accuracy)

**Phase 3 (Ongoing):**
- Pre-trained toxicity model (via Hugging Face; free inference)
- Pre-trained sentiment model (same)
- Auto-generate cluster summaries (optional, v1 = keywords only)

**Tools:**
- Stance: scikit-learn (logistic regression/SVM) + TF-IDF
- Toxicity/Sentiment: Hugging Face transformers (zero-shot or fine-tuned)
- Embeddings: sentence-transformers local (all-MiniLM-L6-v2, ~80MB)

---

## Database Schema

### Core Tables

```sql
-- Topics (one per distinct subject)
CREATE TABLE topics (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,  -- e.g., "player_name_transfer", "manager_sacked"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'active'  -- 'active', 'paused', 'archived'
);

-- Posts (Reddit posts matching filters)
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    external_id VARCHAR(50) NOT NULL,  -- Reddit post ID
    platform VARCHAR(20) DEFAULT 'reddit',
    title VARCHAR(500) NOT NULL,
    selftext TEXT,
    author_hash VARCHAR(64),  -- SHA256(username)
    score INTEGER,
    created_utc BIGINT NOT NULL,
    permalink VARCHAR(500),
    last_processed_utc BIGINT,  -- Last time we fetched comments for this post
    stored_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, external_id)
);

-- Comments (Reddit comments)
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    external_id VARCHAR(50) NOT NULL,  -- Reddit comment ID
    platform VARCHAR(20) DEFAULT 'reddit',
    body TEXT NOT NULL,
    author_hash VARCHAR(64),
    score INTEGER,
    created_utc BIGINT NOT NULL,
    parent_comment_id VARCHAR(50),  -- Reddit parent comment ID (null if direct reply to post)
    permalink VARCHAR(500),
    stored_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, external_id)
);

-- Classifications
CREATE TABLE classifications (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    stance VARCHAR(20) NOT NULL,  -- 'SUPPORT', 'OPPOSE', 'MIXED', 'NEUTRAL'
    sentiment VARCHAR(20) NOT NULL,  -- 'POSITIVE', 'NEUTRAL', 'NEGATIVE'
    toxicity_score FLOAT DEFAULT NULL,  -- 0.0–1.0
    model_version VARCHAR(50),  -- e.g., "v1_logistic_regression"
    classified_at TIMESTAMP DEFAULT NOW(),
    classified_by VARCHAR(50) DEFAULT 'model'  -- 'model', 'manual', 'rule'
);

-- Embeddings (vectors for clustering)
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    comment_id INTEGER NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    embedding VECTOR(384),  -- sentence-transformers all-MiniLM-L6-v2 = 384 dims
    computed_at TIMESTAMP DEFAULT NOW()
);

-- Clusters (argument groups)
CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    stance VARCHAR(20) NOT NULL,  -- Clusters grouped by stance
    cluster_label INTEGER NOT NULL,  -- KMeans cluster ID (0, 1, 2, ...)
    size INTEGER,  -- Number of comments in cluster
    keywords VARCHAR(500),  -- Top 5–10 keywords, comma-separated
    representative_comment_id INTEGER REFERENCES comments(id),  -- Closest to centroid
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(topic_id, stance, cluster_label)
);

-- Denormalized daily stats (for timeline)
CREATE TABLE daily_stats (
    id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    stance_support_count INTEGER DEFAULT 0,
    stance_oppose_count INTEGER DEFAULT 0,
    stance_mixed_count INTEGER DEFAULT 0,
    stance_neutral_count INTEGER DEFAULT 0,
    avg_toxicity_score FLOAT DEFAULT NULL,
    total_comments INTEGER DEFAULT 0,
    computed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(topic_id, date)
);
```

### Indexes (Critical for Performance)
```sql
CREATE INDEX idx_posts_topic ON posts(topic_id);
CREATE INDEX idx_comments_topic ON comments(topic_id);
CREATE INDEX idx_comments_post ON comments(post_id);
CREATE INDEX idx_comments_created ON comments(created_utc);
CREATE INDEX idx_classifications_comment ON classifications(comment_id);
CREATE INDEX idx_embeddings_comment ON embeddings(comment_id);
CREATE INDEX idx_clusters_topic_stance ON clusters(topic_id, stance);
CREATE INDEX idx_daily_stats_topic_date ON daily_stats(topic_id, date);
```

### Database Constraints

**Data Integrity:**
- Foreign key constraints (cascade delete on topic removal)
- Unique constraints (no duplicate posts/comments from Reddit)
- Check constraints (stance/sentiment must be valid enums)

**Storage Limits:**
- Max 25,000 comments per topic
- Max 1,000 comments per post
- Max 2,000 comments ingested per 30-min cycle
- Purge comments older than 6 months (background job, weekly)

---

## Architecture & Tech Stack

### Backend Architecture

```
┌─────────────────┐
│  Reddit API     │
└────────┬────────┘
         │ (PRAW/aiohttp)
         ▼
┌─────────────────────┐
│  Data Ingestion     │
│  (fetch_pipeline)   │ ◄─── Scheduled every 30 min
├─────────────────────┤      via APScheduler
│ - Keyword filter    │
│ - Dedup by ID       │
│ - Clean text        │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  PostgreSQL         │
│  (SQLAlchemy ORM)   │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Classification     │
│  (stance/sentiment) │ ◄─── On-demand or scheduled
├─────────────────────┤
│ - Rule-based filter │
│ - Trained model     │
│ - Toxicity API      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Embedding & Clust  │
│  (semantic analysis)│
├─────────────────────┤
│ - sentence-xformers │
│ - scikit-learn      │
│ - Auto-labeling     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Analytics/Stats    │
│  (timeline, trends) │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  FastAPI (REST)     │
│  /api/topics        │
│  /api/comments      │
│  /api/clusters      │
│  /api/timeline      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Frontend (React)   │
│  Dashboard          │
└─────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Runtime** | Python 3.10+ |
| **Framework** | FastAPI 0.100+ |
| **Database** | PostgreSQL 14+ (local or Railway) |
| **ORM** | SQLAlchemy 2.0 |
| **Async HTTP** | aiohttp |
| **Reddit API** | PRAW 7.7+ |
| **Scheduling** | APScheduler 3.10+ |
| **ML/NLP** | scikit-learn, sentence-transformers |
| **Embeddings** | all-MiniLM-L6-v2 (huggingface-hub) |
| **Toxicity/Sentiment** | Hugging Face transformers (zero-shot) |
| **Data validation** | Pydantic v2 |
| **Testing** | pytest |
| **CLI** | Click (for admin commands) |
| **Frontend** | React 18, Vite, Tailwind CSS |
| **Charting** | Plotly.js or Chart.js |
| **Deployment** | Docker, Railway |

### Directory Structure

```
social-debate-analyzer/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry
│   │   ├── config.py                  # Settings (env vars)
│   │   ├── database.py                # SQLAlchemy setup + session
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── topic.py               # Topic model
│   │   │   ├── post.py                # Post model
│   │   │   ├── comment.py             # Comment model
│   │   │   ├── classification.py      # Stance/sentiment/toxicity
│   │   │   ├── embedding.py           # Vector embeddings
│   │   │   └── cluster.py             # Argument clusters
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── topic_schema.py        # Pydantic models
│   │   │   ├── comment_schema.py
│   │   │   └── cluster_schema.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── topics.py              # GET /api/topics
│   │   │   ├── comments.py            # GET /api/comments
│   │   │   ├── clusters.py            # GET /api/clusters
│   │   │   ├── timeline.py            # GET /api/timeline
│   │   │   └── health.py              # GET /health
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── reddit_fetcher.py      # PRAW + data cleaning
│   │   │   ├── classifier.py          # Stance/sentiment/toxicity
│   │   │   ├── embedder.py            # Sentence-transformers wrapper
│   │   │   ├── clusterer.py           # KMeans + label extraction
│   │   │   ├── analytics.py           # Timeline/stats computation
│   │   │   └── storage.py             # DB transaction wrappers
│   │   └── tasks/
│   │       ├── __init__.py
│   │       ├── scheduler.py           # APScheduler setup
│   │       ├── fetch_job.py           # Periodic fetch task
│   │       ├── classify_job.py        # Periodic classification
│   │       └── cluster_job.py         # Periodic clustering
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_classifier.py
│   │   ├── test_embedder.py
│   │   ├── test_reddit_fetcher.py
│   │   └── conftest.py                # pytest fixtures
│   ├── migrations/                    # Alembic (if using)
│   │   └── ...
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment template
│   └── README.md                      # Backend setup guide
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── TimelineChart.tsx
│   │   │   ├── ClusterView.tsx
│   │   │   ├── ToxicityHeatmap.tsx
│   │   │   ├── TopArguments.tsx
│   │   │   └── CommentList.tsx
│   │   ├── pages/
│   │   │   ├── TopicPage.tsx
│   │   │   └── ExploreTopics.tsx
│   │   ├── hooks/
│   │   │   ├── useTopics.ts
│   │   │   └── useClusters.ts
│   │   ├── api/
│   │   │   └── client.ts              # API client functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── README.md                      # Frontend setup guide
│
├── .github/
│   └── workflows/
│       └── deploy.yml                 # CI/CD pipeline
│
├── docker-compose.yml                 # Local dev stack
├── Dockerfile.backend
├── Dockerfile.frontend
├── .gitignore
├── PROJECT_SPECIFICATION.md           # This file
└── README.md                          # Project overview
```

---

## API Specification

### Base URL
- **Local:** `http://localhost:8000`
- **Production:** `https://your-app.railway.app`

### Endpoints

#### 1. Topics API

**GET /api/topics**
- Returns list of all topics
- Response:
```json
{
  "topics": [
    {
      "id": 1,
      "name": "haaland_transfer",
      "comment_count": 12543,
      "post_count": 87,
      "created_at": "2026-02-15T10:00:00Z",
      "status": "active"
    }
  ]
}
```

**POST /api/topics**
- Create new topic
- Body:
```json
{
  "name": "new_topic_name",
  "keywords": ["keyword1", "keyword2"]
}
```

**GET /api/topics/{topic_id}**
- Get topic details + stats
- Response:
```json
{
  "id": 1,
  "name": "haaland_transfer",
  "total_comments": 12543,
  "total_posts": 87,
  "stance_breakdown": {
    "SUPPORT": 4500,
    "OPPOSE": 3200,
    "MIXED": 2100,
    "NEUTRAL": 2743
  },
  "avg_toxicity": 0.28,
  "date_range": ["2026-01-19", "2026-02-19"],
  "last_updated": "2026-02-19T14:30:00Z"
}
```

#### 2. Comments API

**GET /api/comments?topic_id=1&limit=50&offset=0**
- Get comments for topic
- Query params:
  - `topic_id` (required)
  - `stance` (optional): SUPPORT, OPPOSE, MIXED, NEUTRAL
  - `sentiment` (optional): POSITIVE, NEUTRAL, NEGATIVE
  - `toxicity_min`, `toxicity_max` (optional): filter by toxicity range
  - `limit`, `offset` (pagination)
  - `sort_by` (optional): scored, newest, most_relevant

- Response:
```json
{
  "total": 12543,
  "comments": [
    {
      "id": 1,
      "body": "Great signing for City, Haaland will be world class",
      "author_hash": "a1b2c3...",
      "created_utc": 1708346400,
      "score": 245,
      "stance": "SUPPORT",
      "sentiment": "POSITIVE",
      "toxicity_score": 0.05,
      "permalink": "https://reddit.com/r/soccer/comments/..._/...",
      "parent_comment_id": "comment123"
    }
  ]
}
```

#### 3. Clusters API

**GET /api/clusters?topic_id=1&stance=SUPPORT**
- Get argument clusters for topic
- Query params:
  - `topic_id` (required)
  - `stance` (optional): SUPPORT, OPPOSE, MIXED, NEUTRAL (if omitted, return all)

- Response:
```json
{
  "topic_id": 1,
  "clusters": [
    {
      "id": 1,
      "stance": "SUPPORT",
      "cluster_label": 0,
      "size": 1203,
      "keywords": ["world class", "best signing", "premier league", "talent", "young"],
      "representative_comment": {
        "id": 543,
        "body": "He's one of the best young strikers in the world, amazing signing",
        "author_hash": "xyz789...",
        "score": 187
      },
      "top_quotes": [
        {
          "id": 543,
          "body": "He's the best young striker in the world",
          "score": 187
        },
        {
          "id": 544,
          "body": "World class talent, will be a phenomenal signing",
          "score": 156
        }
      ]
    }
  ],
  "total_comments": 12543,
  "clustering_date": "2026-02-19T12:00:00Z"
}
```

#### 4. Timeline API

**GET /api/timeline?topic_id=1&date_from=2026-01-19&date_to=2026-02-19**
- Get daily stance breakdown
- Response:
```json
{
  "topic_id": 1,
  "timeline": [
    {
      "date": "2026-02-19",
      "stance_support_count": 120,
      "stance_oppose_count": 85,
      "stance_mixed_count": 45,
      "stance_neutral_count": 67,
      "support_pct": 0.38,
      "oppose_pct": 0.27,
      "mixed_pct": 0.14,
      "neutral_pct": 0.21,
      "avg_toxicity": 0.26,
      "total_comments": 317
    }
  ]
}
```

#### 5. Health Check

**GET /health**
- Returns:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "last_fetch": "2026-02-19T14:30:00Z",
  "db_connection": "ok",
  "scheduler_status": "running"
}
```

---

## Frontend Requirements

### Pages

#### 1. Topic Explorer
- List all topics
- Create new topic (input: name + keywords)
- Search/filter topics

#### 2. Topic Dashboard
- **Sidebar:** Topic info + stats
- **Main area:** 
  - **Timeline chart** (stance % over time, last 30 days)
  - **Toxicity trend** (line/bar chart)
  - **Stance distribution** (pie chart or bars)
- **Filters:** Stance, sentiment, toxicity range
- **Auto-refresh:** Every 5 minutes

#### 3. Top Arguments View
- Show clusters (grouped by stance: SUPPORT, OPPOSE, MIXED, NEUTRAL)
- For each cluster:
  - Keywords (5–10, displayed as tags)
  - Cluster size + percentage
  - Representative quote (linked to full comment on Reddit)
  - Top 3 quotes with Reddit links
  - Collapse/expand per cluster
- Sort clusters by size (descending)
- Only show clusters with ≥8 comments

#### 4. Comment List View
- Paginated list of all comments for topic
- Each comment shows:
  - Body (truncated, expandable)
  - Author hash (anonymized)
  - Score (Reddit upvotes)
  - Stance badge (SUPPORT/OPPOSE/MIXED/NEUTRAL)
  - Sentiment badge (POSITIVE/NEUTRAL/NEGATIVE)
  - Toxicity score (0.0–1.0, color-coded: green/yellow/red)
  - Link to original Reddit thread
- Filters: stance, sentiment, toxicity range
- Sort: by score, newest, most relevant

### Visual Design

**Color Scheme:**
- SUPPORT: green (#10b981)
- OPPOSE: red (#ef4444)
- MIXED: orange (#f59e0b)
- NEUTRAL: gray (#6b7280)
- POSITIVE sentiment: light green
- NEGATIVE sentiment: light red
- Toxicity: green (0–0.33) → yellow (0.33–0.67) → red (0.67–1.0)

**Layout:**
- Responsive design (mobile-friendly)
- Sticky navbar with topic selector
- Sidebar collapsible on mobile
- Dashboard grid: 1 col on mobile, 2–3 cols on desktop

### Tech Stack
- **Framework:** React 18
- **Build tool:** Vite
- **Styling:** Tailwind CSS
- **Charts:** Plotly.js for interactive charts
- **API client:** axios or fetch wrapper
- **State:** Context API or TanStack Query (for API caching)
- **Routing:** React Router v6

---

## Implementation Phases

### Phase 0: Setup (Day 0)
- [x] Create GitHub repo
- [ ] Set up Python venv
- [ ] Install dependencies (requirements.txt)
- [ ] Set up PostgreSQL locally (docker-compose)
- [ ] Create .env.example + .env
- [ ] Initialize database schema (Alembic or raw SQL)
- [ ] Set up FastAPI hello world
- [ ] Set up Node.js + Vite frontend

**Deliverable:** Hello world API + blank dashboard

### Phase 1: Data Pipeline (Days 1–3)
**Backend:**
- [ ] PRAW + Reddit authentication
- [ ] Keyword filtering logic
- [ ] fetch_job.py (periodic task to fetch posts + comments)
- [ ] Clean text + deduplication logic
- [ ] Store in PostgreSQL via SQLAlchemy
- [ ] /api/comments endpoint (basic list)
- [ ] Monitoring/logging for fetch job

**Testing:**
- [ ] Fetch 100+ comments successfully
- [ ] Verify deduplication
- [ ] Check database schema (no orphaned records, correct counts)

**Deliverable:** 5k–10k comments in database, auto-updating every 30 min

### Phase 2: Classification (Days 3–5)
**Backend:**
- [ ] Set up sentence-transformers embeddings (local)
- [ ] Label 150–250 comments manually (across all stance classes)
- [ ] Build standalone classification script (rule-based + trained model)
- [ ] Integrate into classify_job.py (periodic task)
- [ ] Store classifications in DB
- [ ] Pre-trained toxicity model (Hugging Face)
- [ ] Pre-trained sentiment model (Hugging Face)
- [ ] /api/comments endpoint (include classifications)

**Testing:**
- [ ] Classifier accuracy on test set: >70%
- [ ] Confusion matrix + error analysis
- [ ] Toxicity/sentiment model sanity check

**Deliverable:** All comments classified with stance/sentiment/toxicity

### Phase 3: Clustering & Analytics (Days 5–7)
**Backend:**
- [ ] Embedding computation + storage (for all comments)
- [ ] KMeans clustering (per stance bucket, 8–12 clusters each)
- [ ] Auto-label clusters (keywords + representative quote)
- [ ] cluster_job.py (re-cluster daily/weekly)
- [ ] /api/clusters endpoint
- [ ] analytics.py (daily stats + timeline)
- [ ] /api/timeline endpoint
- [ ] /api/topics/{id} endpoint (full stats)

**Testing:**
- [ ] Clusters are semantically coherent (manual review)
- [ ] Keywords make sense
- [ ] Timeline data correct (sum of daily == total)

**Deliverable:** Clusters + timeline data ready for frontend

### Phase 4: Frontend (Days 7–10)
**React:**
- [ ] Topic explorer page (list topics + create)
- [ ] Topic dashboard page (layout + sidebar)
- [ ] Timeline chart (Plotly)
- [ ] Stance distribution (pie/bar chart)
- [ ] Toxicity trend (line chart)
- [ ] Top arguments view (clusters + quotes)
- [ ] Comment list view (paginated, filterable)
- [ ] Auto-refresh every 5 min
- [ ] Mobile responsive design
- [ ] Error handling + loading states

**Testing:**
- [ ] All pages load without errors
- [ ] Filters work correctly
- [ ] Charts display correct data
- [ ] Links to Reddit work

**Deliverable:** Fully functional dashboard (MVP)

### Phase 5: Deployment & Polish (Days 10–14)
**Backend:**
- [ ] Add logging + monitoring
- [ ] Write API tests (pytest)
- [ ] Docker setup (backend Dockerfile)
- [ ] Deploy to Railway (PostgreSQL + API)
- [ ] Environment variables configured

**Frontend:**
- [ ] Write component tests
- [ ] Build optimization (code splitting, lazy loading)
- [ ] Docker setup (frontend Dockerfile)
- [ ] Deploy to Vercel or Railway
- [ ] Point to production API

**Documentation:**
- [ ] README (setup + usage)
- [ ] API docs (auto-generated by FastAPI)
- [ ] GitHub wiki (optional)

**Deliverable:** Live app at public URL

### Phase 6: Iteration (Days 14–21)
- [ ] User testing + feedback
- [ ] Bug fixes
- [ ] Model improvements (expand labeled data to 500+)
- [ ] Performance optimization (query indexing, caching)
- [ ] Nice-to-haves:
  - [ ] Network graph of reply chains (optional)
  - [ ] Sentiment word clouds
  - [ ] Toxicity heatmap (optional)
  - [ ] Search comments by keyword
  - [ ] Export data (CSV, JSON)

---

## Quality Gates & Validation

### Data Quality

| Gate | Condition | Action |
|------|-----------|--------|
| Duplicate comments | >1% duplicates | Stop ingestion, investigate |
| Missing classifications | >5% unclassified after 24h | Flag in dashboard |
| Cluster size | Cluster with <8 comments | Don't show in UI |
| Quote quality | Representative quote <40 chars | Don't show |
| Minimum data | <300 classified comments for topic | Show "not enough data" banner |

### Model Quality

| Metric | Target | Tool |
|--------|--------|------|
| Stance accuracy | >70% on test set | Confusion matrix (sklearn) |
| Stance F1 (macro) | >0.65 | Per-class F1 scores |
| Toxicity correlation | High agreement with human review (10% sample) | Manual spot-check |
| Cluster coherence | Manual review: clusters are semantically related | Read top 5 quotes per cluster |

### Evaluation Process (Week 3)

**Day 1–2:**
- Label 150 comments (balanced across stance classes)
- Train model on 100, test on 50
- Compute confusion matrix + accuracy

**Day 2–3:**
- Error analysis: where does model fail?
- Identify common misclassifications
- Expand labeled data to 250 if time permits

**Day 3:**
- Manual review of clusters (do they make sense?)
- Spot-check toxicity scores (10 comments, does score match tone?)
- Check timeline data (do counts match raw comment data?)

### Dashboard Quality Gates

- ✅ Timeline chart: sum of stance buckets = total comments (daily)
- ✅ Cluster view: all clusters ranked by size, sorted descending
- ✅ No NaN or null values in visualizations
- ✅ Links to Reddit work (permalink is valid)
- ✅ Comments with stance NEUTRAL < 50% (rule-based filter is working)

---

## Deployment

### Local Development

**Prerequisites:**
- Python 3.10+
- PostgreSQL 14+
- Node.js 18+
- Git

**Setup (Backend):**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your Reddit API credentials + DB connection

# Initialize database
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

**Setup (Frontend):**

```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
```

**Full Stack (Docker Compose):**

```bash
docker-compose up -d
# PostgreSQL: localhost:5432
# FastAPI: http://localhost:8000
# React: http://localhost:5173
```

### Production Deployment

**Platform:** Railway.app

**Deployment Steps:**

1. **PostgreSQL:**
   - Create Railway project
   - Add PostgreSQL plugin
   - Get connection string
   - Run migrations: `alembic upgrade head`

2. **FastAPI:**
   - Connect GitHub repo
   - Set environment variables:
     - REDDIT_CLIENT_ID
     - REDDIT_CLIENT_SECRET
     - REDDIT_USER_AGENT
     - DATABASE_URL
     - ENVIRONMENT=production
   - Deploy (auto on push to main)
   - Health check: GET /health

3. **React:**
   - Deploy to Vercel OR Railway
   - Set API endpoint (env var)
   - Trigger auto-deploy on push

**Environment Variables:**

```env
# Backend (.env)
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=MyBot/1.0 (by u/your_username)
SCHEDULER_ENABLED=true
LOG_LEVEL=info

# Frontend (.env)
VITE_API_BASE_URL=https://your-api.railway.app
VITE_ENVIRONMENT=production
```

**Monitoring:**
- Railway dashboard (CPU, memory, logs)
- APScheduler job logs (stored in DB)
- FastAPI logs → stdout (captured by Railway)
- Sentry integration (optional, for error tracking)

---

## Testing Strategy

### Unit Tests

**Backend (pytest):**
- `test_classifier.py`: Stance/sentiment/toxicity classification
- `test_embedder.py`: Embedding generation + vector math
- `test_reddit_fetcher.py`: Keyword filtering, deduplication
- `test_clusterer.py`: KMeans clustering, label extraction

**Frontend (Vitest or Jest):**
- Component tests: Dashboard, TimelineChart, ClusterView
- Hook tests: useTopics, useClusters
- API client tests: Mocking axios/fetch

### Integration Tests
- Full pipeline: fetch → classify → cluster → timeline
- E2E test: Create topic → wait for data → query API → verify results

### Manual Testing Checklist
- [ ] Reddit fetching works and rate limits respected
- [ ] Comments display correctly on dashboard
- [ ] Filters work (stance, sentiment, toxicity)
- [ ] Charts update every 5 minutes
- [ ] Links to Reddit are valid
- [ ] Mobile layout is usable
- [ ] Deployment doesn't break anything

---

## Stretch Goals (v2+)

If you finish the MVP early and still have time:

1. **Multi-subreddit support**
   - Add 2–3 more subreddits (r/news, r/worldnews)
   - Display stance heatmap by subreddit
   - Compare topics across subreddits

2. **Network graph of reply chains**
   - Visualize argument threads
   - See how arguments evolve in a discussion
   - Highlight "winning" arguments (highest score)

3. **Argument evolution**
   - Track how clusters change over time
   - Show new arguments emerging
   - Detect when opinions shift

4. **Multi-language**
   - Detect language (langdetect)
   - Support Spanish + English initially
   - Translate summaries (optional)

5. **Alerts & subscriptions**
   - Email notification when stance shifts >10% in a day
   - Notify when new major argument cluster appears
   - Summary email weekly

6. **Expand ML (if you love it)**
   - Fine-tune stance classifier on 500+ labeled examples
   - Aspect-based sentiment (stance per player, per tactic, etc.)
   - Argument quality scoring (evidence-based vs. emotional)

7. **Export & sharing**
   - Export topic analysis as PDF report
   - Share dashboard snapshots on social media
   - Embed charts on external websites

8. **Admin panel**
   - Manually label comments for training
   - Adjust classifier thresholds
   - Monitor scheduler health
   - Delete/hide topics

---

## Troubleshooting & Common Issues

| Problem | Solution |
|---------|----------|
| Reddit API rate limit | Implement exponential backoff + cache post metadata |
| Duplicate comments | Store external_id, use UNIQUE constraint |
| Slow clustering | Run clustering as batch job (not per-request), cache results |
| High toxicity scores everywhere | Check model calibration; may need different threshold |
| Clusters don't make semantic sense | Increase number of clusters, or reduce to fewer larger clusters |
| Dashboard slow on 10k+ comments | Add pagination, index on created_utc, lazy-load charts |
| Embeddings take forever to compute | Use all-MiniLM-L6-v2 (fast), batch computation, cache |

---

## Key Success Metrics

By end of 3 weeks, you should have:

- ✅ **10k+ comments** in database
- ✅ **Stance classifier** >70% accuracy
- ✅ **5–10 argument clusters** per stance (semantically coherent)
- ✅ **Timeline chart** showing stance trends
- ✅ **Working dashboard** with filters + pagination
- ✅ **Deployed to production** (Railway)
- ✅ **Ability to add new topics** without code changes
- ✅ **Automated updates** every 30 minutes

---

## Additional Resources

- **PRAW docs:** https://praw.readthedocs.io/
- **Sentence-transformers:** https://www.sbert.net/
- **scikit-learn clustering:** https://scikit-learn.org/modules/cluster.html
- **FastAPI:** https://fastapi.tiangolo.com/
- **Hugging Face Hub:** https://huggingface.co/
- **Railway:** https://railway.app/docs
- **Vercel:** https://vercel.com/docs

---

**Last Updated:** February 19, 2026  
**Next Review:** After Phase 1 (Day 3)
