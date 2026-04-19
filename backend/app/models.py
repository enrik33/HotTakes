"""
Database ORM models using SQLAlchemy 2.0.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    ForeignKey,
    BigInteger,
    DateTime,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Topic(Base):
    """Topic model - one topic per debate subject."""

    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, default="")
    status = Column(String(50), default="active")  # active, paused, archived
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    posts = relationship("Post", back_populates="topic", cascade="all, delete-orphan")
    comments = relationship(
        "Comment", back_populates="topic", cascade="all, delete-orphan"
    )
    clusters = relationship(
        "Cluster", back_populates="topic", cascade="all, delete-orphan"
    )
    daily_stats = relationship(
        "DailyStats", back_populates="topic", cascade="all, delete-orphan"
    )


class Post(Base):
    """HN story model."""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    external_id = Column(String(50), nullable=False)  # HN item ID
    platform = Column(String(20), default="hackernews")
    title = Column(String(500), nullable=False)
    selftext = Column(Text)
    author_hash = Column(String(64))  # SHA256 hash of username
    score = Column(Integer, default=0)
    created_utc = Column(BigInteger, nullable=False)
    permalink = Column(String(500))
    last_processed_utc = Column(BigInteger)  # Last time we fetched comments for this
    stored_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        # Unique constraint on (platform, external_id)
    )

    # Relationships
    topic = relationship("Topic", back_populates="posts")
    comments = relationship(
        "Comment", back_populates="post", cascade="all, delete-orphan"
    )


class Comment(Base):
    """HN comment model."""

    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    external_id = Column(String(50), nullable=False)  # HN item ID
    platform = Column(String(20), default="hackernews")
    body = Column(Text, nullable=False)
    author_hash = Column(String(64))  # SHA256 hash of HN username
    score = Column(Integer, default=0)
    created_utc = Column(BigInteger, nullable=False, index=True)
    parent_comment_id = Column(
        String(50)
    )  # Parent HN item ID (null if direct reply to story)
    permalink = Column(String(500))
    stored_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("Topic", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    classification = relationship(
        "Classification",
        back_populates="comment",
        uselist=False,
        cascade="all, delete-orphan",
    )
    embedding = relationship(
        "Embedding",
        back_populates="comment",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Classification(Base):
    """Stance, sentiment, and toxicity classification."""

    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(
        Integer, ForeignKey("comments.id"), nullable=False, index=True, unique=True
    )
    stance = Column(String(20), nullable=False)  # SUPPORT, OPPOSE, MIXED, NEUTRAL
    sentiment = Column(String(20), nullable=False)  # POSITIVE, NEUTRAL, NEGATIVE
    toxicity_score = Column(Float)  # 0.0–1.0
    model_version = Column(String(50), default="v1")  # Tracking for model updates
    classified_at = Column(DateTime, default=datetime.utcnow)
    classified_by = Column(String(50), default="model")  # model, manual, rule

    # Relationships
    comment = relationship("Comment", back_populates="classification")


class Embedding(Base):
    """Semantic embeddings for clustering."""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    comment_id = Column(
        Integer, ForeignKey("comments.id"), nullable=False, index=True, unique=True
    )
    embedding_vector = Column(
        String(5000)
    )  # JSON-serialized float list (or use pgvector if using PostgreSQL)
    computed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    comment = relationship("Comment", back_populates="embedding")


class Cluster(Base):
    """Argument clusters (groups of similar comments)."""

    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    stance = Column(
        String(20), nullable=False
    )  # SUPPORT, OPPOSE, MIXED, NEUTRAL (clustering within stance)
    cluster_label = Column(Integer, nullable=False)  # KMeans cluster ID (0, 1, 2, ...)
    size = Column(Integer, default=0)  # Number of comments in cluster
    keywords = Column(String(500))  # Comma-separated keywords
    representative_comment_id = Column(
        Integer, ForeignKey("comments.id")
    )  # Comment closest to centroid
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("Topic", back_populates="clusters")

    __table_args__ = (
        # Unique constraint on (topic_id, stance, cluster_label)
    )


class DailyStats(Base):
    """Denormalized daily statistics for timeline."""

    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    stance_support_count = Column(Integer, default=0)
    stance_oppose_count = Column(Integer, default=0)
    stance_mixed_count = Column(Integer, default=0)
    stance_neutral_count = Column(Integer, default=0)
    avg_toxicity_score = Column(Float)
    total_comments = Column(Integer, default=0)
    computed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    topic = relationship("Topic", back_populates="daily_stats")

    __table_args__ = (
        # Unique constraint on (topic_id, date)
    )
