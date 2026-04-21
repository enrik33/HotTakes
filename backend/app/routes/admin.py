"""
Admin endpoints for manually triggering background jobs.
"""

import threading
import traceback

from fastapi import APIRouter

from app.logging_config import get_logger
from app.tasks.scheduler import (
    classify_comments,
    cluster_arguments,
    compute_daily_stats,
)

router = APIRouter()
logger = get_logger(__name__, component="admin")


def _run_in_background(job_name: str, fn):
    """Fire the job in a daemon thread so the HTTP response returns immediately."""

    def _target():
        try:
            fn()
        except Exception as exc:
            logger.error(
                "admin_job_error",
                extra={
                    "event": "admin_job_error",
                    "component": "admin",
                    "request_id": "-",
                    "job_name": job_name,
                    "error": str(exc),
                },
            )

    t = threading.Thread(target=_target, daemon=True)
    t.start()


@router.post("/admin/run/ingest", tags=["admin"])
async def trigger_ingest():
    """Trigger a Hacker News ingestion run immediately."""
    from app.tasks.fetch_job import run_fetch_job  # noqa: PLC0415

    _run_in_background("fetch_hn", run_fetch_job)
    return {"status": "started", "job": "ingest"}


@router.post("/admin/run/classify", tags=["admin"])
async def trigger_classify():
    """Trigger comment classification immediately (background)."""
    _run_in_background("classify", classify_comments)
    return {"status": "started", "job": "classify"}


@router.post("/admin/run/classify/sync", tags=["admin"])
async def trigger_classify_sync():
    """Run classification synchronously until all comments are classified, then return totals."""
    from app.database import SessionLocal  # noqa: PLC0415
    from app.tasks.classify_job import run_classify_job  # noqa: PLC0415

    db = SessionLocal()
    try:
        totals = {"classified": 0, "gated": 0, "errors": 0}
        while True:
            result = run_classify_job(db)
            for k in totals:
                totals[k] += result.get(k, 0)
            if result.get("classified", 0) + result.get("gated", 0) == 0:
                break
        return {"status": "ok", "job": "classify", "result": totals}
    except Exception as exc:
        return {
            "status": "error",
            "job": "classify",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        db.close()


@router.post("/admin/run/cluster", tags=["admin"])
async def trigger_cluster():
    """Trigger embedding generation + opinion clustering immediately."""
    _run_in_background("cluster", cluster_arguments)
    return {"status": "started", "job": "cluster"}


@router.post("/admin/run/cluster/sync", tags=["admin"])
async def trigger_cluster_sync():
    """Run embedding + clustering synchronously and return result."""
    from app.database import SessionLocal  # noqa: PLC0415
    from app.models import Topic  # noqa: PLC0415
    from app.services.clusterer import run_clustering_for_topic  # noqa: PLC0415
    from app.services.embedder import generate_comment_embeddings  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415

    db = SessionLocal()
    try:
        embed_result = generate_comment_embeddings(db)
        topic_ids = [
            row[0]
            for row in db.execute(
                select(Topic.id).where(Topic.status == "active")
            ).all()
        ]
        cluster_results = []
        for tid in topic_ids:
            r = run_clustering_for_topic(db, topic_id=tid)
            cluster_results.append(r)
        return {"status": "ok", "embed": embed_result, "clusters": cluster_results}
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    finally:
        db.close()


@router.post("/admin/run/stats", tags=["admin"])
async def trigger_stats():
    """Trigger daily stats computation immediately."""
    _run_in_background("stats", compute_daily_stats)
    return {"status": "started", "job": "stats"}
