"""
Scheduler for background tasks using APScheduler.
"""

import time
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.logging_config import get_logger

scheduler = BackgroundScheduler()
logger = get_logger(__name__, component="scheduler")

# Exponential backoff delays between retry attempts (seconds)
_RETRY_DELAYS = [5, 15, 45]
_MAX_ATTEMPTS = len(_RETRY_DELAYS) + 1  # 3 delays → 4 total attempts, but we use 3


def _run_job(job_name: str, component: str, fn):
    """Run scheduled job with retry-on-failure and structured metrics logs.

    Retries up to 3 times with exponential backoff (5 s → 15 s → 45 s).
    Emits a ``job_metrics`` log on completion regardless of outcome.
    """
    logger.info(
        "job_started",
        extra={
            "event": "job_started",
            "component": component,
            "request_id": "-",
            "job_name": job_name,
        },
    )
    start = time.monotonic()
    last_exc: Exception | None = None
    attempts = 0

    for attempt_idx, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            time.sleep(delay)
        attempts += 1
        try:
            fn()
            duration_s = round(time.monotonic() - start, 3)
            logger.info(
                "job_succeeded",
                extra={
                    "event": "job_succeeded",
                    "component": component,
                    "request_id": "-",
                    "job_name": job_name,
                },
            )
            logger.info(
                "job_metrics",
                extra={
                    "event": "job_metrics",
                    "component": component,
                    "request_id": "-",
                    "job_name": job_name,
                    "duration_s": duration_s,
                    "attempts": attempts,
                    "success": True,
                },
            )
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "job_attempt_failed",
                extra={
                    "event": "job_attempt_failed",
                    "component": component,
                    "request_id": "-",
                    "job_name": job_name,
                    "attempt": attempts,
                    "error": str(exc),
                },
            )

    # All attempts exhausted
    duration_s = round(time.monotonic() - start, 3)
    logger.exception(
        "job_failed",
        extra={
            "event": "job_failed",
            "component": component,
            "request_id": "-",
            "job_name": job_name,
        },
        exc_info=last_exc,
    )
    logger.error(
        "job_metrics",
        extra={
            "event": "job_metrics",
            "component": component,
            "request_id": "-",
            "job_name": job_name,
            "duration_s": duration_s,
            "attempts": attempts,
            "success": False,
        },
    )


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        from app.tasks.fetch_job import run_fetch_job

        now = datetime.now(timezone.utc)

        scheduler.add_job(
            lambda: _run_job("fetch_hn", "ingestion", run_fetch_job),
            trigger=IntervalTrigger(minutes=settings.fetch_interval_minutes),
            id="fetch_hn",
            name="Fetch Hacker News data",
            replace_existing=True,
            next_run_time=now,
        )
        scheduler.add_job(
            lambda: _run_job("classify", "classification", classify_comments),
            trigger=IntervalTrigger(hours=settings.classify_interval_hours),
            id="classify",
            name="Classify comments",
            replace_existing=True,
            max_instances=1,
            next_run_time=now,
        )
        scheduler.add_job(
            lambda: _run_job("cluster", "clustering", cluster_arguments),
            trigger=IntervalTrigger(hours=settings.cluster_interval_hours),
            id="cluster",
            name="Cluster arguments",
            replace_existing=True,
            max_instances=1,
            next_run_time=now,
        )
        scheduler.add_job(
            lambda: _run_job("stats", "scheduler", compute_daily_stats),
            trigger=IntervalTrigger(hours=settings.stats_job_interval_hours),
            id="stats",
            name="Compute daily stats",
            replace_existing=True,
            max_instances=1,
            next_run_time=now,
        )
        scheduler.start()
        logger.info(
            "scheduler_started",
            extra={
                "event": "scheduler_started",
                "component": "scheduler",
                "request_id": "-",
                "job_name": None,
            },
        )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info(
            "scheduler_stopped",
            extra={
                "event": "scheduler_stopped",
                "component": "scheduler",
                "request_id": "-",
                "job_name": None,
            },
        )


# Task functions (to be implemented)


def classify_comments():
    """Classify unclassified comments — loops until none remain."""
    from app.database import SessionLocal  # noqa: PLC0415
    from app.tasks.classify_job import run_classify_job  # noqa: PLC0415

    db = SessionLocal()
    try:
        total = {"classified": 0, "gated": 0, "errors": 0}
        while True:
            result = run_classify_job(db)
            for k in total:
                total[k] += result.get(k, 0)
            if result.get("classified", 0) + result.get("gated", 0) == 0:
                break
    finally:
        db.close()


def cluster_arguments():
    """Generate embeddings and argument clusters for all active topics."""
    from sqlalchemy import select  # noqa: PLC0415

    from app.database import SessionLocal  # noqa: PLC0415
    from app.models import Topic  # noqa: PLC0415
    from app.services.clusterer import run_clustering_for_topic  # noqa: PLC0415
    from app.services.embedder import generate_comment_embeddings  # noqa: PLC0415

    db = SessionLocal()
    try:
        # Generate embeddings for any unembedded comments first
        generate_comment_embeddings(db)

        topic_ids = [
            row[0]
            for row in db.execute(
                select(Topic.id).where(Topic.status == "active")
            ).all()
        ]
        for tid in topic_ids:
            run_clustering_for_topic(db, topic_id=tid)
    finally:
        db.close()


def compute_daily_stats():
    """Compute daily statistics for all active topics."""
    from app.database import SessionLocal  # noqa: PLC0415
    from app.services.analytics import run_daily_stats  # noqa: PLC0415

    db = SessionLocal()
    try:
        run_daily_stats(db, topic_id=None)
    finally:
        db.close()
