"""Tests for the comments API route (Issue #38)."""

from __future__ import annotations

import os
import random

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_comments_api.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Classification, Comment, Post, Topic  # noqa: E402

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
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_topic(db) -> Topic:
    topic = Topic(name="Test Topic", description="desc")
    db.add(topic)
    db.flush()
    return topic


def _seed_post(db, topic_id: int) -> Post:
    post = Post(
        topic_id=topic_id,
        external_id=str(random.randint(100000, 999999)),
        title="Test Post",
        created_utc=1700000000,
    )
    db.add(post)
    db.flush()
    return post


def _seed_comment(
    db,
    topic_id: int,
    post_id: int,
    body: str = "Test comment body",
    score: int = 5,
    stance: str | None = None,
) -> Comment:
    comment = Comment(
        topic_id=topic_id,
        post_id=post_id,
        external_id=str(random.randint(100000, 999999)),
        body=body,
        author_hash="abc123def456",
        score=score,
        created_utc=1700000000,
    )
    db.add(comment)
    db.flush()
    if stance:
        clf = Classification(
            comment_id=comment.id,
            stance=stance,
            sentiment="NEUTRAL",
            toxicity_score=0.1,
        )
        db.add(clf)
        db.flush()
    return comment


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCommentsApiBasic:
    def test_missing_topic_id_returns_422(self):
        resp = client.get("/api/comments")
        assert resp.status_code == 422

    def test_empty_topic_returns_empty_list(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/comments?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["comments"] == []
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_unknown_topic_returns_empty_list(self):
        resp = client.get("/api/comments?topic_id=99999")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["comments"] == []

    def test_returns_seeded_comments(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            _seed_comment(db, topic.id, post.id, body="First comment", score=10)
            _seed_comment(db, topic.id, post.id, body="Second comment", score=20)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/comments?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["comments"]) == 2

    def test_comment_fields_present(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            _seed_comment(db, topic.id, post.id, stance="SUPPORT")
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/comments?topic_id={topic_id}")
        assert resp.status_code == 200
        c = resp.json()["comments"][0]
        assert "id" in c
        assert "body" in c
        assert "author_hash" in c
        assert "score" in c
        assert "stance" in c
        assert "sentiment" in c
        assert "toxicity_score" in c

    def test_comment_without_classification_defaults_to_neutral(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            _seed_comment(db, topic.id, post.id)  # no stance
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/comments?topic_id={topic_id}")
        assert resp.status_code == 200
        c = resp.json()["comments"][0]
        assert c["stance"] == "NEUTRAL"
        assert c["toxicity_score"] == 0.0


class TestCommentsApiFilters:
    def test_stance_filter(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            _seed_comment(
                db, topic.id, post.id, body="Support comment", stance="SUPPORT"
            )
            _seed_comment(db, topic.id, post.id, body="Oppose comment", stance="OPPOSE")
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/comments?topic_id={topic_id}&stance=SUPPORT")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["comments"][0]["stance"] == "SUPPORT"

    def test_limit_and_offset(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            for i in range(5):
                _seed_comment(db, topic.id, post.id, body=f"Comment {i}")
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/comments?topic_id={topic_id}&limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 5
        assert len(body["comments"]) == 2

    def test_sort_by_scored(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            _seed_comment(db, topic.id, post.id, body="Low score", score=1)
            _seed_comment(db, topic.id, post.id, body="High score", score=100)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/comments?topic_id={topic_id}&sort_by=scored")
        assert resp.status_code == 200
        comments = resp.json()["comments"]
        assert comments[0]["score"] >= comments[1]["score"]

    def test_invalid_sort_by_returns_422(self):
        resp = client.get("/api/comments?topic_id=1&sort_by=invalid_value")
        assert resp.status_code == 422
