# HotTakes Ops Runbook

Operational procedures for the HotTakes production deployment (Railway backend + Vercel frontend).

---

## Architecture

```
Vercel (frontend)           Railway (backend)           Railway Postgres
  React SPA          →   FastAPI + APScheduler   →   PostgreSQL 15
  vercel.json              railway.toml
  /api/* rewrite        port $PORT (Railway)
```

---

## Health Checks

**Backend health endpoint**
```
GET https://YOUR_RAILWAY_URL/health
```
Expected response (200):
```json
{ "status": "ok", "scheduler_running": true, "database": "connected" }
```

**Check from CLI (Railway shell or local)**
```bash
curl -s https://YOUR_RAILWAY_URL/health | python -m json.tool
```

**Docker (local dev)**
```bash
docker logs hottakes_backend --tail 50
docker exec -it hottakes_backend curl -s http://localhost:8000/health
```

---

## Startup & Shutdown

**Local dev**
```bash
# Start all services
docker compose up -d

# Stop
docker compose down

# Full reset (drops DB data)
docker compose down -v
```

**Production (Railway)**
Deployments are triggered automatically on push to `main`. To manually redeploy:
- Railway dashboard → Service → "Redeploy"

---

## Scheduler Job Management

Jobs run in-process via APScheduler. Enable with `SCHEDULER_ENABLED=true`.

| Job | Frequency | Function |
|-----|-----------|----------|
| `fetch_hn` | Every 30 min | Ingest HN stories matching keywords |
| `classify` | Every 6 hours | Classify unclassified comments |
| `cluster` | Every 12 hours | Cluster arguments by stance |
| `stats` | Every 1 hour | Compute daily_stats rows |

**Verify scheduler is running**
```bash
# Check health endpoint
curl -s https://YOUR_RAILWAY_URL/health | python -m json.tool
# Look for: "scheduler_running": true

# Railway logs — look for job_started / job_succeeded events
railway logs --tail 100 | grep -E "job_started|job_succeeded|job_failed"
```

---

## Ingestion Failures (fetch_hn stops)

**Symptoms**: No new posts/comments after 1+ hours, `total_posts` in health not growing.

**Investigation**
```bash
# Production
railway logs --tail 200 | grep -E "job_failed|fetch_error|hn_client"

# Local
docker logs hottakes_backend --tail 100 | grep -E "job_failed|fetch_error"
```

**Recovery — trigger manual ingestion (local)**
```bash
docker exec -it hottakes_backend python - <<'EOF'
from app.tasks.fetch_job import run_fetch_job
run_fetch_job()
EOF
```

**Recovery — production (Railway shell)**
```bash
python - <<'EOF'
from app.tasks.fetch_job import run_fetch_job
run_fetch_job()
EOF
```

---

## Classification Lag Recovery

**Symptoms**: Comments exist but clusters say "not enough classified comments".

**Check unclassified count**
```bash
docker exec -it hottakes_backend python - <<'EOF'
from app.database import SessionLocal
from app.models import Comment, Classification
from sqlalchemy import select
db = SessionLocal()
total = db.query(Comment).count()
classified = db.query(Classification).count()
print(f"Total: {total}, Classified: {classified}, Pending: {total - classified}")
db.close()
EOF
```

**Trigger manual classify + cluster**
```bash
docker exec -it hottakes_backend python - <<'EOF'
from app.database import SessionLocal
from app.tasks.classify_job import run_classify_job
from app.services.clusterer import run_clustering_for_topic
from app.services.analytics import run_daily_stats
from app.models import Topic
db = SessionLocal()
run_classify_job(db)
topic_ids = [t.id for t in db.query(Topic).all()]
for tid in topic_ids:
    run_clustering_for_topic(db, topic_id=tid)
run_daily_stats(db, topic_id=None)
db.commit()
db.close()
print("Done")
EOF
```

---

## Database Connectivity Failures

**Symptoms**: 500 errors on all API endpoints, health returns `"database": "error"`.

**Check connection**
```bash
# Local
docker exec -it hottakes_postgres psql -U debateuser -d social_debate -c "\dt"

# Production — Railway dashboard → Postgres → "Connect" tab → query console
SELECT COUNT(*) FROM comments;
```

**Restart backend**
```bash
# Local
docker compose restart backend

# Production
Railway dashboard → Backend service → "Restart"
```

---

## Log Inspection

```bash
# All ERROR-level events (local)
docker logs hottakes_backend 2>&1 | grep ERROR

# Specific job failures
docker logs hottakes_backend 2>&1 | grep job_failed

# Recent 50 lines
docker logs hottakes_backend --tail 50

# Follow live
docker logs hottakes_backend -f

# Production (Railway CLI)
railway logs --tail 100
railway logs --tail 100 | grep ERROR
```

---

## Database Backups

### Automatic Backups (Production — Railway)

Railway Postgres provides **daily automatic backups** with a **7-day rolling retention window** on the free plan (Starter plan provides longer retention).

- View and restore backups: Railway dashboard → Postgres plugin → "Backups" tab
- Point-in-time restore is available on paid plans

### Manual Backup (Extra Snapshot)

**From local Docker**
```bash
docker exec -t hottakes_postgres pg_dump \
  -U debateuser social_debate \
  --no-owner --no-acl \
  > backup_$(date +%Y%m%d_%H%M%S).sql
```

**From Railway (requires Railway CLI + psql)**
```bash
# Get connection string from Railway dashboard → Postgres → "Connect"
pg_dump "$DATABASE_URL" --no-owner --no-acl > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Procedure

```bash
# Local
docker exec -i hottakes_postgres psql -U debateuser social_debate < backup_YYYYMMDD.sql

# Production — restore to a fresh Railway Postgres instance
psql "$DATABASE_URL" < backup_YYYYMMDD.sql
```

---

## Useful Queries

```sql
-- Comment volume by topic
SELECT t.name, COUNT(c.id) AS comments
FROM topics t LEFT JOIN comments c ON c.topic_id = t.id
GROUP BY t.id ORDER BY comments DESC;

-- Classification coverage
SELECT
  COUNT(*) AS total_comments,
  SUM(CASE WHEN cl.id IS NOT NULL THEN 1 ELSE 0 END) AS classified,
  ROUND(100.0 * SUM(CASE WHEN cl.id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct
FROM comments c
LEFT JOIN classifications cl ON cl.comment_id = c.id;

-- Stance distribution
SELECT stance, COUNT(*) FROM classifications GROUP BY stance ORDER BY COUNT(*) DESC;

-- Recent ingestion activity
SELECT title, created_utc FROM posts ORDER BY created_utc DESC LIMIT 10;
```

---

## See Also

- [README.md](../README.md) — project overview and local setup
- [RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md) — MVP launch gates
