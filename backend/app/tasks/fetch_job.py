"""
Periodic HN fetch job.

Wraps HNIngestionService with:
- Overlap prevention: a single threading.Event flag prevents concurrent runs.
- Structured logging: start / end / duration / counts logged on every execution.
"""

import asyncio
import threading
from datetime import datetime, timezone

from app.logging_config import get_logger

logger = get_logger(__name__, component="ingestion")

# Guards against overlapping fetch runs (e.g. if a cycle takes longer than the
# configured interval).
_running = threading.Event()


def run_fetch_job() -> None:
    """
    Execute one HN ingestion cycle.

    Safe to call from APScheduler's BackgroundScheduler thread pool.  If a
    previous cycle is still in progress the call returns immediately so that
    overlapping runs never occur.
    """
    if _running.is_set():
        logger.warning(
            "fetch_job_skipped_overlap",
            extra={
                "event": "fetch_job_skipped_overlap",
                "component": "ingestion",
                "request_id": "-",
                "job_name": "fetch_hn",
            },
        )
        return

    _running.set()
    started_at = datetime.now(tz=timezone.utc)
    logger.info(
        "fetch_job_started",
        extra={
            "event": "fetch_job_started",
            "component": "ingestion",
            "request_id": "-",
            "job_name": "fetch_hn",
            "started_at": started_at.isoformat(),
        },
    )

    try:
        result = asyncio.run(_run_ingestion())
        finished_at = datetime.now(tz=timezone.utc)
        duration_s = round((finished_at - started_at).total_seconds(), 2)
        logger.info(
            "fetch_job_completed",
            extra={
                "event": "fetch_job_completed",
                "component": "ingestion",
                "request_id": "-",
                "job_name": "fetch_hn",
                "duration_s": duration_s,
                **result,
            },
        )
    except Exception:
        finished_at = datetime.now(tz=timezone.utc)
        duration_s = round((finished_at - started_at).total_seconds(), 2)
        logger.exception(
            "fetch_job_failed",
            extra={
                "event": "fetch_job_failed",
                "component": "ingestion",
                "request_id": "-",
                "job_name": "fetch_hn",
                "duration_s": duration_s,
            },
        )
    finally:
        _running.clear()


async def _run_ingestion() -> dict:
    """Open a DB session and run one ingestion cycle. Returns result metrics."""
    from app.database import SessionLocal
    from app.services.hn_client import HNClient
    from app.services.hn_ingestion import HNIngestionService

    db = SessionLocal()
    try:
        async with HNClient() as client:
            service = HNIngestionService(db=db, client=client)
            return await service.run()
    finally:
        db.close()
