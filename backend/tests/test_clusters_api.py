"""Tests for the clusters API top-quotes and route behavior (Issue #28)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_clusters_api.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Cluster, Comment, Post, Topic  # noqa: E402

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_db():
    # Re-assert the DB override in case another test module changed it
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def bypass_quality_gate():
    """Set quality gate threshold to 0 so basic cluster tests pass without 300+ classifications."""
    import app.routes.clusters as m

    original = m._MIN_CLASSIFIED_COMMENTS
    m._MIN_CLASSIFIED_COMMENTS = 0
    yield
    m._MIN_CLASSIFIED_COMMENTS = original


def _seed_topic(db) -> Topic:
    topic = Topic(name="Test Topic", description="desc")
    db.add(topic)
    db.flush()
    return topic


def _seed_post(db, topic_id: int) -> Post:
    import random

    post = Post(
        topic_id=topic_id,
        external_id=str(random.randint(100000, 999999)),
        title="Test Post",
        created_utc=1700000000,
    )
    db.add(post)
    db.flush()
    return post


def _seed_cluster(
    db, topic_id: int, stance: str = "SUPPORT", label: int = 0
) -> Cluster:
    cluster = Cluster(
        topic_id=topic_id,
        stance=stance,
        cluster_label=label,
        size=5,
    )
    db.add(cluster)
    db.flush()
    return cluster


def _seed_comment(
    db,
    topic_id: int,
    post_id: int,
    cluster_id: int,
    body: str,
    score: int = 10,
) -> Comment:
    import random

    c = Comment(
        topic_id=topic_id,
        post_id=post_id,
        external_id=str(random.randint(100000, 999999)),
        body=body,
        author_hash="abc123",
        score=score,
        created_utc=1700000000,
        cluster_id=cluster_id,
    )
    db.add(c)
    db.flush()
    return c


class TestGetClustersBasic:
    def test_empty_topic_returns_empty_clusters(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["topic_id"] == topic_id
        assert body["clusters"] == []
        assert body["total_comments"] == 0

    def test_cluster_fields_present(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_cluster(db, topic.id)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        assert resp.status_code == 200
        c = resp.json()["clusters"][0]
        assert "id" in c
        assert "stance" in c
        assert "cluster_label" in c
        assert "size" in c
        assert "keywords" in c
        assert "top_quotes" in c
        assert "representative_comment" in c

    def test_stance_filter_works(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_cluster(db, topic.id, stance="SUPPORT", label=0)
            _seed_cluster(db, topic.id, stance="OPPOSE", label=0)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}&stance=SUPPORT")
        assert resp.status_code == 200
        clusters = resp.json()["clusters"]
        assert len(clusters) == 1
        assert clusters[0]["stance"] == "SUPPORT"


class TestTopQuotes:
    def test_top_quotes_limited_to_three(self):
        long_body = "a" * 50
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            cluster = _seed_cluster(db, topic.id)
            for i in range(6):
                _seed_comment(
                    db, topic.id, post.id, cluster.id, long_body + str(i), score=i
                )
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        quotes = resp.json()["clusters"][0]["top_quotes"]
        assert len(quotes) <= 3

    def test_short_comments_excluded_from_top_quotes(self):
        from app.config import settings

        short_body = "x" * (settings.min_quote_length - 1)
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            cluster = _seed_cluster(db, topic.id)
            _seed_comment(db, topic.id, post.id, cluster.id, short_body, score=100)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        quotes = resp.json()["clusters"][0]["top_quotes"]
        assert quotes == []

    def test_top_quotes_ordered_by_score_desc(self):
        long_body = "b" * 50
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            cluster = _seed_cluster(db, topic.id)
            _seed_comment(db, topic.id, post.id, cluster.id, long_body + "low", score=1)
            _seed_comment(
                db, topic.id, post.id, cluster.id, long_body + "high", score=99
            )
            _seed_comment(
                db, topic.id, post.id, cluster.id, long_body + "mid", score=50
            )
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        quotes = resp.json()["clusters"][0]["top_quotes"]
        scores = [q["score"] for q in quotes]
        assert scores == sorted(scores, reverse=True)

    def test_duplicate_bodies_deduped(self):
        body = "c" * 50  # identical first 100 chars
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            cluster = _seed_cluster(db, topic.id)
            _seed_comment(db, topic.id, post.id, cluster.id, body, score=5)
            _seed_comment(db, topic.id, post.id, cluster.id, body, score=4)
            _seed_comment(db, topic.id, post.id, cluster.id, body, score=3)
            _seed_comment(db, topic.id, post.id, cluster.id, body, score=2)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        quotes = resp.json()["clusters"][0]["top_quotes"]
        # All identical → only 1 unique body
        assert len(quotes) == 1

    def test_top_quote_fields(self):
        body = "d" * 50
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            cluster = _seed_cluster(db, topic.id)
            _seed_comment(db, topic.id, post.id, cluster.id, body, score=10)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        quote = resp.json()["clusters"][0]["top_quotes"][0]
        assert "id" in quote
        assert "body" in quote
        assert "author_hash" in quote
        assert "score" in quote

    def test_no_comments_top_quotes_empty(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_cluster(db, topic.id)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        quotes = resp.json()["clusters"][0]["top_quotes"]
        assert quotes == []
