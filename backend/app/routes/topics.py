"""
Topics API endpoints.
"""

from fastapi import APIRouter, Depends
from app.database import get_db
from app.errors import raise_api_error
from app.models import Topic, Comment, Classification
from app.schemas.error import ErrorResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter()


class TopicCreate(BaseModel):
    name: str
    description: str = ""


class TopicResponse(BaseModel):
    id: int
    name: str
    description: str
    status: str
    post_count: int = 0
    comment_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


@router.get("/topics")
async def list_topics(db: Session = Depends(get_db)):
    """Get all topics."""
    topics = db.query(Topic).all()
    result = []
    for topic in topics:
        result.append(
            {
                "id": topic.id,
                "name": topic.name,
                "description": topic.description,
                "status": topic.status,
                "post_count": len(topic.posts),
                "comment_count": len(topic.comments),
                "created_at": topic.created_at.isoformat(),
                "updated_at": topic.updated_at.isoformat(),
            }
        )
    return {"topics": result}


@router.post(
    "/topics",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Topic already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "TOPIC_ALREADY_EXISTS",
                            "message": "Topic already exists",
                            "details": None,
                        },
                        "request_id": "optional-id",
                    }
                }
            },
        }
    },
)
async def create_topic(topic: TopicCreate, db: Session = Depends(get_db)):
    """Create a new topic."""
    existing = db.query(Topic).filter(Topic.name == topic.name).first()
    if existing:
        raise_api_error(
            status_code=400,
            code="TOPIC_ALREADY_EXISTS",
            message="Topic already exists",
        )

    new_topic = Topic(name=topic.name, description=topic.description)
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)

    return {
        "id": new_topic.id,
        "name": new_topic.name,
        "description": new_topic.description,
        "status": new_topic.status,
    }


@router.get(
    "/topics/{topic_id}",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Topic not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "TOPIC_NOT_FOUND",
                            "message": "Topic not found",
                            "details": None,
                        },
                        "request_id": "optional-id",
                    }
                }
            },
        }
    },
)
async def get_topic(topic_id: int, db: Session = Depends(get_db)):
    """Get topic details and stats."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise_api_error(
            status_code=404,
            code="TOPIC_NOT_FOUND",
            message="Topic not found",
        )

    # Count by stance
    from sqlalchemy import func

    stance_counts = (
        db.query(Classification.stance, func.count(Classification.id))
        .join(Comment)
        .filter(Comment.topic_id == topic_id)
        .group_by(Classification.stance)
        .all()
    )

    stance_breakdown = {
        "SUPPORT": 0,
        "OPPOSE": 0,
        "MIXED": 0,
        "NEUTRAL": 0,
    }
    for stance, count in stance_counts:
        stance_breakdown[stance] = count

    return {
        "id": topic.id,
        "name": topic.name,
        "description": topic.description,
        "total_comments": len(topic.comments),
        "total_posts": len(topic.posts),
        "status": topic.status,
        "stance_breakdown": stance_breakdown,
        "created_at": topic.created_at.isoformat(),
        "updated_at": topic.updated_at.isoformat(),
        "last_updated": (
            max([c.stored_at for c in topic.comments]).isoformat()
            if topic.comments
            else None
        ),
    }
