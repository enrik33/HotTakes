# HotTakes - MVP Project Specification

## 1. Product Goal

HotTakes analyzes debate patterns in `r/soccer` and turns large comment streams into readable argument summaries.

MVP goals:

- ingest relevant posts/comments
- classify stance/sentiment/toxicity
- cluster semantically similar arguments
- expose API for timeline and top-argument views

## 2. Scope

- Platform (MVP): Reddit only
- Subreddit: `r/soccer`
- Topic domain: player performances + transfers
- History window: 30 days
- Update interval: every 30 minutes

Target volume:

- posts: 80-200
- comments: 8,000-30,000

## 3. Ingestion Rules

Post matching is case-insensitive title/selftext matching.

Transfer keywords:

- transfer, transfers, here we go, hwg
- signed, signing, joins, loan, on loan
- fee, release clause, contract, wages
- bid, offer, agreement, medical
- rumour, rumor, reported, linked, interest
- deal, announcement, confirmed, official

Performance/manager keywords:

- motm, man of the match
- performance, form, bottled, carry job
- tactics, system, lineup, selection, subs
- manager, coach, sacked

Optional rule:

- include posts if `(player name + transfer keyword)` matches

## 4. Data Model Constraints

MVP remains Reddit-only while schema is expansion-ready.

Store:

- `platform`
- `external_id`
- `permalink`
- `created_utc`
- `author_hash` (no raw usernames)
- parent relationships for comment threading

Limits:

- max comments/topic: 25,000
- max comments/post: 1,000
- max comments/fetch: 2,000

Retention:

- hard strategy supports up to 6 months
- MVP collection focus is last 1 month

## 5. Classification

Stance labels:

- `SUPPORT`
- `OPPOSE`
- `MIXED`
- `NEUTRAL`

Policy:

- one comment -> one stance label
- no per-aspect stance in MVP
- comments that do not reference thread target -> auto `NEUTRAL`

Sentiment labels:

- `POSITIVE`, `NEUTRAL`, `NEGATIVE`

Toxicity:

- numeric score `0.0-1.0` (UI may map to Low/Medium/High)

## 6. Stance Target Definition

Stance is anchored to the post intent:

- transfer posts: approval/disapproval of transfer move
- performance/decision posts: agreement/disagreement with the take

This avoids ambiguous "stance about what" labeling.

## 7. Clustering

Similarity definition:

- semantic similarity via embeddings + cosine distance
- cluster within stance buckets to keep outputs readable

Cluster policy:

- target 8-12 clusters per stance bucket
- show top 5-10 largest clusters in UI
- per-cluster output:
  - 5-10 keywords/phrases
  - 1 representative quote
  - top 3 quotes

## 8. Quality Gates

- do not show clusters `< 8` comments
- drop low-signal quotes (`< 40` chars)
- if classified comments `< 300`, show "not enough data yet" and skip clustering view

## 9. MVP Features

Primary:

- Top arguments (cluster summaries + quotes)
- Timeline (stance percentages over time)
- Toxicity trend + toxicity-by-stance

Secondary:

- word clouds by stance

Deferred (v2+):

- multi-subreddit heatmaps
- reply-chain network graph
- websocket live updates

Dashboard refresh:

- every 5 minutes (polling)

## 10. Tech Stack

- API: FastAPI
- ORM: SQLAlchemy 2.0
- Scheduler: APScheduler
- Async HTTP: aiohttp
- Clustering: scikit-learn
- DB for MVP: PostgreSQL (run locally first)

## 11. Implementation Order

1. Local backend stability
2. Reddit fetch + filtering
3. Target-aware stance gating
4. Baseline classifier (150-250 labeled comments)
5. Embedding + clustering
6. Timeline/toxicity aggregations
7. Frontend dashboard
8. Cloud deployment (Railway/Render)

## 12. Success Definition (MVP)

- stable ingestion from `r/soccer`
- useful top-argument clusters
- stance/timeline insights are visible and interpretable
- private deployment usable by single operator
