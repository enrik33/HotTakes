"""
Timeline API endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DailyStats
from typing import Optional

router = APIRouter()


@router.get("/timeline")
async def get_timeline(
    topic_id: int,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get daily stance breakdown for timeline."""
    query = db.query(DailyStats).filter(DailyStats.topic_id == topic_id)

    if date_from:
        query = query.filter(DailyStats.date >= date_from)
    if date_to:
        query = query.filter(DailyStats.date <= date_to)

    stats = query.order_by(DailyStats.date.asc()).all()

    result = []
    for stat in stats:
        total = (
            stat.stance_support_count
            + stat.stance_oppose_count
            + stat.stance_mixed_count
            + stat.stance_neutral_count
        )

        result.append(
            {
                "date": stat.date,
                "stance_support_count": stat.stance_support_count,
                "stance_oppose_count": stat.stance_oppose_count,
                "stance_mixed_count": stat.stance_mixed_count,
                "stance_neutral_count": stat.stance_neutral_count,
                "support_pct": stat.stance_support_count / total if total > 0 else 0,
                "oppose_pct": stat.stance_oppose_count / total if total > 0 else 0,
                "mixed_pct": stat.stance_mixed_count / total if total > 0 else 0,
                "neutral_pct": stat.stance_neutral_count / total if total > 0 else 0,
                "avg_toxicity": stat.avg_toxicity_score,
                "total_comments": stat.total_comments,
            }
        )

    return {
        "topic_id": topic_id,
        "timeline": result,
    }
