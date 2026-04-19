"""
Classification batch job.

Fetches unclassified comments from the database in batches and runs all three
classifiers (stance gate → stance model, sentiment, toxicity), then writes
``Classification`` rows.

Designed to be called from the APScheduler job in ``scheduler.py``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Classification, Comment
from app.services.sentiment_service import classify_sentiment_batch
from app.services.stance_classifier import classify_stance_batch
from app.services.stance_gate import is_on_target, split_target_terms
from app.services.toxicity_service import score_toxicity_batch

logger = logging.getLogger(__name__)

_BATCH_SIZE = 50


def run_classify_job(db: Session) -> dict:
    """Classify up to ``_BATCH_SIZE`` unclassified comments.

    Comments without a ``Classification`` row are selected ordered by
    ``created_utc ASC`` so older comments are processed first.

    Returns
    -------
    dict
        ``{"classified": int, "gated": int, "errors": int}``
        *gated*   — comments auto-labelled NEUTRAL by the stance gate (no ML).
        *classified* — comments that went through the full ML pipeline.
        *errors*  — per-comment failures that were skipped.
    """
    # -----------------------------------------------------------------
    # 1. Query unclassified comments (LEFT JOIN → missing classification)
    # -----------------------------------------------------------------
    stmt = (
        select(Comment)
        .outerjoin(Classification, Classification.comment_id == Comment.id)
        .where(Classification.id.is_(None))
        .where(Comment.body.isnot(None))
        .where(Comment.body != "")
        .order_by(Comment.created_utc.asc())
        .limit(_BATCH_SIZE)
        .options(joinedload(Comment.post))
    )
    comments: list[Comment] = list(db.execute(stmt).scalars().unique())

    if not comments:
        logger.info(
            "classify_no_pending",
            extra={
                "event": "classify_no_pending",
                "component": "classification",
                "request_id": "-",
                "job_name": "classify",
            },
        )
        return {"classified": 0, "gated": 0, "errors": 0}

    # -----------------------------------------------------------------
    # 2. Split into "gated" (off-topic → NEUTRAL) vs "to classify"
    # -----------------------------------------------------------------
    gated_comments: list[Comment] = []
    model_comments: list[Comment] = []

    for comment in comments:
        target_terms = split_target_terms(
            comment.post.target_terms if comment.post else None
        )
        if target_terms and not is_on_target(comment.body, target_terms):
            gated_comments.append(comment)
        else:
            model_comments.append(comment)

    # -----------------------------------------------------------------
    # 3. Write gated classifications (rule-based, no ML)
    # -----------------------------------------------------------------
    gated_count = 0
    error_count = 0

    for comment in gated_comments:
        try:
            db.add(
                Classification(
                    comment_id=comment.id,
                    stance="NEUTRAL",
                    sentiment="NEUTRAL",
                    toxicity_score=0.0,
                    model_version=settings.stance_classifier_model,
                    classified_at=datetime.now(timezone.utc),
                    classified_by="rule",
                )
            )
            gated_count += 1
        except Exception:
            logger.exception(
                "classify_gated_write_failed",
                extra={
                    "event": "classify_gated_write_failed",
                    "component": "classification",
                    "request_id": "-",
                    "job_name": "classify",
                    "comment_id": comment.id,
                },
            )
            error_count += 1

    # -----------------------------------------------------------------
    # 4. Run ML classifiers on the remaining comments
    # -----------------------------------------------------------------
    classified_count = 0

    if model_comments:
        bodies = [c.body for c in model_comments]

        # Sentiment and toxicity are target-agnostic — batch the whole set.
        try:
            sentiments = classify_sentiment_batch(bodies, batch_size=32)
        except Exception:
            logger.exception(
                "classify_sentiment_batch_failed",
                extra={
                    "event": "classify_sentiment_batch_failed",
                    "component": "classification",
                    "request_id": "-",
                    "job_name": "classify",
                },
            )
            sentiments = ["NEUTRAL"] * len(model_comments)

        try:
            toxicity_scores = score_toxicity_batch(bodies, batch_size=32)
        except Exception:
            logger.exception(
                "classify_toxicity_batch_failed",
                extra={
                    "event": "classify_toxicity_batch_failed",
                    "component": "classification",
                    "request_id": "-",
                    "job_name": "classify",
                },
            )
            toxicity_scores = [0.0] * len(model_comments)

        # Stance is target-specific — run one at a time to vary target_terms.
        stances: list[str] = []
        for comment in model_comments:
            target_terms = split_target_terms(
                comment.post.target_terms if comment.post else None
            )
            try:
                result = classify_stance_batch(
                    [comment.body], target_terms=target_terms, batch_size=1
                )
                stances.append(result[0])
            except Exception:
                logger.exception(
                    "classify_stance_item_failed",
                    extra={
                        "event": "classify_stance_item_failed",
                        "component": "classification",
                        "request_id": "-",
                        "job_name": "classify",
                        "comment_id": comment.id,
                    },
                )
                stances.append("NEUTRAL")

        # Write classification rows
        for comment, stance, sentiment, tox in zip(
            model_comments, stances, sentiments, toxicity_scores
        ):
            try:
                db.add(
                    Classification(
                        comment_id=comment.id,
                        stance=stance,
                        sentiment=sentiment,
                        toxicity_score=tox,
                        model_version=settings.stance_classifier_model,
                        classified_at=datetime.now(timezone.utc),
                        classified_by="model",
                    )
                )
                classified_count += 1
            except Exception:
                logger.exception(
                    "classify_model_write_failed",
                    extra={
                        "event": "classify_model_write_failed",
                        "component": "classification",
                        "request_id": "-",
                        "job_name": "classify",
                        "comment_id": comment.id,
                    },
                )
                error_count += 1

    db.commit()

    logger.info(
        "classify_job_done",
        extra={
            "event": "classify_job_done",
            "component": "classification",
            "request_id": "-",
            "job_name": "classify",
            "classified": classified_count,
            "gated": gated_count,
            "errors": error_count,
        },
    )

    return {
        "classified": classified_count,
        "gated": gated_count,
        "errors": error_count,
    }
