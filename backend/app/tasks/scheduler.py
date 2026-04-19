"""
Scheduler for background tasks using APScheduler.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.logging_config import get_logger

scheduler = BackgroundScheduler()
logger = get_logger(__name__, component="scheduler")


def _run_job(job_name: str, component: str, fn):
    """Run scheduled job with consistent structured logs."""
    logger.info(
        "job_started",
        extra={
            "event": "job_started",
            "component": component,
            "request_id": "-",
            "job_name": job_name,
        },
    )
    try:
        fn()
        logger.info(
            "job_succeeded",
            extra={
                "event": "job_succeeded",
                "component": component,
                "request_id": "-",
                "job_name": job_name,
            },
        )
    except Exception:
        logger.exception(
            "job_failed",
            extra={
                "event": "job_failed",
                "component": component,
                "request_id": "-",
                "job_name": job_name,
            },
        )


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        from app.tasks.fetch_job import run_fetch_job

        scheduler.add_job(
            lambda: _run_job("fetch_hn", "ingestion", run_fetch_job),
            trigger=IntervalTrigger(minutes=settings.fetch_interval_minutes),
            id="fetch_hn",
            name="Fetch Hacker News data",
            replace_existing=True,
        )
        scheduler.add_job(
            lambda: _run_job("classify", "classification", classify_comments),
            trigger=IntervalTrigger(hours=settings.classify_interval_hours),
            id="classify",
            name="Classify comments",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.add_job(
            lambda: _run_job("cluster", "clustering", cluster_arguments),
            trigger=IntervalTrigger(hours=settings.cluster_interval_hours),
            id="cluster",
            name="Cluster arguments",
            replace_existing=True,
        )
        scheduler.add_job(
            lambda: _run_job("stats", "scheduler", compute_daily_stats),
            trigger=IntervalTrigger(hours=settings.stats_job_interval_hours),
            id="stats",
            name="Compute daily stats",
            replace_existing=True,
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
    """Classify unclassified comments."""
    from app.database import SessionLocal  # noqa: PLC0415
    from app.tasks.classify_job import run_classify_job  # noqa: PLC0415

    db = SessionLocal()
    try:
        run_classify_job(db)
    finally:
        db.close()


def cluster_arguments():
    """Generate argument clusters for all active topics."""
    from sqlalchemy import select  # noqa: PLC0415

    from app.database import SessionLocal  # noqa: PLC0415
    from app.models import Topic  # noqa: PLC0415
    from app.services.clusterer import run_clustering_for_topic  # noqa: PLC0415

    db = SessionLocal()
    try:
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
