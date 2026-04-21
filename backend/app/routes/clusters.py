"""
Clusters API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Classification, Cluster, Comment
from app.config import settings
from typing import Optional

router = APIRouter()

_TOP_QUOTES_LIMIT = 3
_DEDUP_PREFIX_LEN = 100
# Use setting if provided, otherwise fall back to 10 so topics with <300 comments
# can still show clusters once classified.
_MIN_CLASSIFIED_COMMENTS = getattr(settings, "min_classified_comments", 10)


def _get_top_quotes(db: Session, cluster_id: int) -> list[dict]:
    """Return up to 3 de-duplicated top-scoring comments for a cluster.

    Steps:
      1. Query all comments with this cluster_id.
      2. Filter to body length >= min_quote_length.
      3. Order by score desc, take top 10 as candidates.
      4. De-duplicate by first 100 chars of body.
      5. Return up to 3 results.
    """
    candidates = (
        db.query(Comment)
        .filter(Comment.cluster_id == cluster_id)
        .order_by(Comment.score.desc())
        .limit(10)
        .all()
    )

    seen_prefixes: set[str] = set()
    quotes: list[dict] = []
    for comment in candidates:
        body = comment.body or ""
        if len(body) < settings.min_quote_length:
            continue
        prefix = body[:_DEDUP_PREFIX_LEN]
        if prefix in seen_prefixes:
            continue
        seen_prefixes.add(prefix)
        quotes.append(
            {
                "id": comment.id,
                "body": body,
                "author_hash": comment.author_hash,
                "score": comment.score,
            }
        )
        if len(quotes) >= _TOP_QUOTES_LIMIT:
            break

    return quotes


@router.get("/clusters")
async def get_clusters(
    topic_id: int,
    stance: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get argument clusters for a topic."""
    # Quality gate: require minimum classified comments before showing clusters
    classified_count = (
        db.query(Classification)
        .filter(
            Classification.comment_id.in_(
                db.query(Comment.id).filter(Comment.topic_id == topic_id)
            )
        )
        .count()
    )
    if classified_count < _MIN_CLASSIFIED_COMMENTS:
        return {
            "topic_id": topic_id,
            "clustering_available": False,
            "reason": "insufficient_data",
            "classified_comments": classified_count,
            "required": _MIN_CLASSIFIED_COMMENTS,
        }

    query = db.query(Cluster).filter(Cluster.topic_id == topic_id)

    if stance:
        query = query.filter(Cluster.stance == stance)

    # Sort by size descending
    clusters = query.order_by(Cluster.size.desc()).all()

    result = []
    for cluster in clusters:
        keywords = cluster.keywords.split(",") if cluster.keywords else []

        top_quotes = _get_top_quotes(db, cluster.id)

        # Representative comment (centroid-closest)
        representative = None
        if cluster.representative_comment_id:
            representative_comment = (
                db.query(Comment)
                .filter(Comment.id == cluster.representative_comment_id)
                .first()
            )
            if representative_comment:
                representative = {
                    "id": representative_comment.id,
                    "body": representative_comment.body,
                    "author_hash": representative_comment.author_hash,
                    "score": representative_comment.score,
                }

        result.append(
            {
                "id": cluster.id,
                "stance": cluster.stance,
                "cluster_label": cluster.cluster_label,
                "size": cluster.size,
                "keywords": keywords,
                "representative_comment": representative,
                "top_quotes": top_quotes,
            }
        )

    return {
        "topic_id": topic_id,
        "clusters": result,
        "total_comments": sum(c.size for c in clusters),
        "clustering_date": None,
    }
