"""
Clusters API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Cluster, Comment, Classification
from typing import Optional
import json

router = APIRouter()


@router.get("/clusters")
async def get_clusters(
    topic_id: int,
    stance: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get argument clusters for a topic."""
    query = db.query(Cluster).filter(Cluster.topic_id == topic_id)
    
    if stance:
        query = query.filter(Cluster.stance == stance)
    
    # Sort by size descending
    clusters = query.order_by(Cluster.size.desc()).all()
    
    result = []
    for cluster in clusters:
        keywords = cluster.keywords.split(",") if cluster.keywords else []
        
        # Get top 3 comments in cluster (by score)
        # Note: In real implementation, you'd store cluster membership
        # For now, just get the representative comment
        representative = None
        if cluster.representative_comment_id:
            representative_comment = db.query(Comment).filter(
                Comment.id == cluster.representative_comment_id
            ).first()
            if representative_comment:
                representative = {
                    "id": representative_comment.id,
                    "body": representative_comment.body,
                    "author_hash": representative_comment.author_hash,
                    "score": representative_comment.score,
                }
        
        result.append({
            "id": cluster.id,
            "stance": cluster.stance,
            "cluster_label": cluster.cluster_label,
            "size": cluster.size,
            "keywords": keywords,
            "representative_comment": representative,
            "top_quotes": [representative] if representative else [],
        })
    
    return {
        "topic_id": topic_id,
        "clusters": result,
        "total_comments": sum(c.size for c in clusters),
        "clustering_date": None,  # TODO: Add clustering timestamp
    }
