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
        scheduler.add_job(
            lambda: _run_job("fetch_hn", "ingestion", fetch_hn_data),
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
def fetch_hn_data():
    """Fetch new stories and comments from Hacker News."""
    # TODO: Implement HNIngestionService
    logger.info(
        "fetch_hn_data_stub",
        extra={
            "event": "fetch_hn_data_stub",
            "component": "ingestion",
            "request_id": "-",
            "job_name": "fetch_hn",
        },
    )


def classify_comments():
    """Classify unclassified comments."""
    # TODO: Implement classifier.py
    logger.info(
        "classify_comments_stub",
        extra={
            "event": "classify_comments_stub",
            "component": "classification",
            "request_id": "-",
            "job_name": "classify",
        },
    )


def cluster_arguments():
    """Generate argument clusters."""
    # TODO: Implement clusterer.py
    logger.info(
        "cluster_arguments_stub",
        extra={
            "event": "cluster_arguments_stub",
            "component": "clustering",
            "request_id": "-",
            "job_name": "cluster",
        },
    )


def compute_daily_stats():
    """Compute daily statistics."""
    # TODO: Implement analytics.py
    logger.info(
        "compute_daily_stats_stub",
        extra={
            "event": "compute_daily_stats_stub",
            "component": "scheduler",
            "request_id": "-",
            "job_name": "stats",
        },
    )
