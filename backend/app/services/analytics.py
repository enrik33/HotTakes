"""
Daily stats aggregation service (Issue #30).

Computes per-date stance counts and average toxicity for one or all topics,
writing/updating rows in the ``daily_stats`` table.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from sqlalchemy.orm import Session  # pragma: no cover

logger = logging.getLogger(__name__)


def run_daily_stats(db: "Session", topic_id: int | None = None) -> dict:
    """Aggregate daily stats for one topic or all active topics.

    For each (topic_id, date) pair that has comments with classifications,
    counts stance buckets and computes average toxicity score, then
    upserts a ``DailyStats`` row.

    Parameters
    ----------
    db:
        SQLAlchemy ``Session``.
    topic_id:
        If given, aggregate only that topic.  If ``None``, aggregate all.

    Returns
    -------
    dict
        ``{"topics_processed": int, "rows_upserted": int}``
    """
    from sqlalchemy import cast, func, select  # noqa: PLC0415
    from sqlalchemy.types import Date  # noqa: PLC0415

    from app.models import Classification, Comment, DailyStats, Topic  # noqa: PLC0415

    # ------------------------------------------------------------------
    # 1. Determine which topics to process
    # ------------------------------------------------------------------
    if topic_id is not None:
        topic_ids = [topic_id]
    else:
        topic_ids = [
            row[0]
            for row in db.execute(
                select(Topic.id).where(Topic.status == "active")
            ).all()
        ]

    rows_upserted = 0

    for tid in topic_ids:
        # ------------------------------------------------------------------
        # 2. Group comments by date, join classification
        # ------------------------------------------------------------------
        # We derive the date from Comment.created_utc (unix timestamp)
        # and use SQLAlchemy core to aggregate.
        stmt = (
            select(
                cast(func.to_timestamp(Comment.created_utc), Date).label("date"),
                Classification.stance,
                func.count(Comment.id).label("cnt"),
                func.avg(Classification.toxicity_score).label("avg_tox"),
            )
            .join(Classification, Classification.comment_id == Comment.id)
            .where(Comment.topic_id == tid)
            .group_by(
                cast(func.to_timestamp(Comment.created_utc), Date),
                Classification.stance,
            )
        )
        rows = db.execute(stmt).all()

        # ------------------------------------------------------------------
        # 3. Aggregate per date
        # ------------------------------------------------------------------
        per_date: dict[str, dict] = {}
        for date_str, stance, cnt, avg_tox in rows:
            if date_str not in per_date:
                per_date[date_str] = {
                    "SUPPORT": 0,
                    "OPPOSE": 0,
                    "MIXED": 0,
                    "NEUTRAL": 0,
                    "total": 0,
                    "tox_sum": 0.0,
                    "tox_n": 0,
                }
            d = per_date[date_str]
            if stance in d:
                d[stance] += cnt
            d["total"] += cnt
            if avg_tox is not None:
                d["tox_sum"] += avg_tox * cnt
                d["tox_n"] += cnt

        # ------------------------------------------------------------------
        # 4. Upsert DailyStats rows
        # ------------------------------------------------------------------
        for date_str, agg in per_date.items():
            avg_tox = agg["tox_sum"] / agg["tox_n"] if agg["tox_n"] else None

            existing = (
                db.query(DailyStats)
                .filter(DailyStats.topic_id == tid, DailyStats.date == date_str)
                .first()
            )
            if existing:
                existing.stance_support_count = agg["SUPPORT"]
                existing.stance_oppose_count = agg["OPPOSE"]
                existing.stance_mixed_count = agg["MIXED"]
                existing.stance_neutral_count = agg["NEUTRAL"]
                existing.total_comments = agg["total"]
                existing.avg_toxicity_score = avg_tox
                existing.computed_at = datetime.now(timezone.utc)
            else:
                ds = DailyStats(
                    topic_id=tid,
                    date=date_str,
                    stance_support_count=agg["SUPPORT"],
                    stance_oppose_count=agg["OPPOSE"],
                    stance_mixed_count=agg["MIXED"],
                    stance_neutral_count=agg["NEUTRAL"],
                    total_comments=agg["total"],
                    avg_toxicity_score=avg_tox,
                )
                db.add(ds)
            rows_upserted += 1

        logger.info(
            "daily_stats_topic_done",
            extra={
                "event": "daily_stats_topic_done",
                "component": "analytics",
                "request_id": "-",
                "job_name": "stats",
                "topic_id": tid,
                "dates": len(per_date),
            },
        )

    db.commit()
    return {"topics_processed": len(topic_ids), "rows_upserted": rows_upserted}
