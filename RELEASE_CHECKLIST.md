# HotTakes v2.0.0-MVP Release Checklist

All gates must pass before tagging `v2.0.0-mvp`.

---

## Backend Gates

- [ ] **CI green** — GitHub Actions CI passes on `main` (both `backend` and `frontend` jobs)
- [ ] **Test suite** — `pytest --tb=short -q` passes with ≥ 250 tests, 0 failures
- [ ] **Health endpoint live** — `GET /health` returns `{"status": "ok"}` on the Railway deployment; `last_fetch` timestamp is within the last 1 hour
- [ ] **Ingestion active** — At least 3 HN threads ingested (`SELECT COUNT(*) FROM posts` ≥ 3)
- [ ] **Clustering active** — At least 1 topic has `clustering_available: true` (verified via `GET /api/clusters?topic_id=<id>`)
- [ ] **Timeline populated** — At least 1 topic has ≥ 1 entry in `GET /api/timeline?topic_id=<id>`
- [ ] **Toxicity data present** — At least 1 `DailyStats` row has a non-null `avg_toxicity_score`

## Frontend Gates

- [ ] **Live URL** — Vercel deployment URL is accessible and loads the Topics page
- [ ] **Topics page renders** — Topic cards are visible and navigable
- [ ] **Dashboard functional** — Clusters tab shows stance clusters; Timeline tab renders chart; Toxicity tab renders charts
- [ ] **Auto-refresh works** — Manual "↻ Refresh" button in nav triggers data refetch without page reload
- [ ] **No console errors** — Browser devtools show no uncaught JS errors on any page

## Documentation Gates

- [ ] **README updated** — Includes live Vercel URL, Railway URL, and architecture diagram or description
- [ ] **Ops runbook linked** — `docs/ops_runbook.md` is linked from README

---

## Tagging

Once all gates are checked:

```bash
git tag v2.0.0-mvp
git push origin v2.0.0-mvp
```

Then create a GitHub Release from the tag with a summary of M1–M6 milestones.
