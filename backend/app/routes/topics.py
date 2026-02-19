"""
Topics API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Topic
from pydantic import BaseModel

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
        result.append({
            "id": topic.id,
            "name": topic.name,
            "description": topic.description,
            "status": topic.status,
            "post_count": len(topic.posts),
            "comment_count": len(topic.comments),
            "created_at": topic.created_at.isoformat(),
            "updated_at": topic.updated_at.isoformat(),
        })
    return {"topics": result}


@router.post("/topics")
async def create_topic(topic: TopicCreate, db: Session = Depends(get_db)):
    """Create a new topic."""
    existing = db.query(Topic).filter(Topic.name == topic.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Topic already exists")
    
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


@router.get("/topics/{topic_id}")
async def get_topic(topic_id: int, db: Session = Depends(get_db)):
    """Get topic details and stats."""
    topic = db.query(Topic).filter(Topic.id == topic_id).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    # Count by stance
    from app.models import Classification
    from sqlalchemy import func
    
    stance_counts = db.query(
        Classification.stance,
        func.count(Classification.id)
    ).join(Comment).filter(Comment.topic_id == topic_id).group_by(Classification.stance).all()
    
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
        "last_updated": max([c.stored_at for c in topic.comments]).isoformat() if topic.comments else None,
    }
