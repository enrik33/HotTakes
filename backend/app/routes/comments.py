"""
Comments API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Comment, Classification
from typing import Optional

router = APIRouter()


@router.get("/comments")
async def list_comments(
    topic_id: int,
    stance: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    toxicity_min: Optional[float] = Query(None),
    toxicity_max: Optional[float] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("newest", regex="^(newest|scored|most_relevant)$"),
    db: Session = Depends(get_db),
):
    """Get comments for a topic with optional filters."""
    query = db.query(Comment).filter(Comment.topic_id == topic_id)

    # Filter by stance
    if stance:
        query = query.join(Classification).filter(Classification.stance == stance)

    # Filter by sentiment
    if sentiment:
        query = query.join(Classification).filter(Classification.sentiment == sentiment)

    # Filter by toxicity range
    if toxicity_min is not None or toxicity_max is not None:
        query = query.join(Classification)
        if toxicity_min is not None:
            query = query.filter(Classification.toxicity_score >= toxicity_min)
        if toxicity_max is not None:
            query = query.filter(Classification.toxicity_score <= toxicity_max)

    # Sort
    if sort_by == "scored":
        query = query.order_by(Comment.score.desc())
    elif sort_by == "most_relevant":
        # TODO: Implement relevance scoring (maybe via embedding similarity)
        query = query.order_by(Comment.score.desc())
    else:  # newest
        query = query.order_by(Comment.created_utc.desc())

    # Pagination
    total = query.count()
    comments = query.offset(offset).limit(limit).all()

    result = []
    for comment in comments:
        classification = comment.classification or Classification(
            stance="NEUTRAL", sentiment="NEUTRAL", toxicity_score=0.0
        )
        result.append(
            {
                "id": comment.id,
                "body": comment.body,
                "author_hash": comment.author_hash,
                "created_utc": comment.created_utc,
                "score": comment.score,
                "stance": classification.stance,
                "sentiment": classification.sentiment,
                "toxicity_score": classification.toxicity_score,
                "permalink": comment.permalink,
                "parent_comment_id": comment.parent_comment_id,
            }
        )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "comments": result,
    }
