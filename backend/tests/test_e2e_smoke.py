"""
End-to-end smoke test (Issue #39).

Seeds synthetic HN data → runs clustering → runs daily stats → asserts that
the /api/clusters and /api/timeline endpoints return populated results.

No live HN API calls are made.  Heavy ML models (stance/sentiment/toxicity)
are bypassed by seeding Classification rows directly.  Embeddings are tiny
8-dimensional random vectors so scikit-learn KMeans runs in milliseconds.
"""

from __future__ import annotations

import json
import os
import random

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_e2e_smoke.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Classification, Comment, Embedding, Post, Topic  # noqa: E402
from app.services.analytics import run_daily_stats  # noqa: E402
from app.services.clusterer import run_clustering_for_topic  # noqa: E402

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

# Embedding dimension — small to keep tests fast
_EMBED_DIM = 8
_STANCES = ["SUPPORT", "OPPOSE", "MIXED", "NEUTRAL"]
_COMMENTS_PER_STANCE = 15  # 60 total


@pytest.fixture(autouse=True)
def reset_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def bypass_quality_gate():
    import app.routes.clusters as m
    from app.config import settings

    orig_min_classified = m._MIN_CLASSIFIED_COMMENTS
    orig_min_cluster_size = settings.min_cluster_size
    orig_n_clusters = settings.n_clusters_per_stance

    m._MIN_CLASSIFIED_COMMENTS = 0
    settings.min_cluster_size = 2
    settings.n_clusters_per_stance = 3

    yield

    m._MIN_CLASSIFIED_COMMENTS = orig_min_classified
    settings.min_cluster_size = orig_min_cluster_size
    settings.n_clusters_per_stance = orig_n_clusters


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_pipeline_data() -> int:
    """Seed 2 HN stories + 60 classified + embedded comments.

    Returns the topic_id for use in assertions.
    """
    rng = random.Random(42)
    np_rng = np.random.default_rng(42)

    with TestingSessionLocal() as db:
        # Topic
        topic = Topic(name="AI Safety Debate", description="Synthetic test topic")
        db.add(topic)
        db.flush()

        # Two synthetic HN story posts
        posts = []
        for i in range(2):
            post = Post(
                topic_id=topic.id,
                external_id=str(rng.randint(1_000_000, 9_999_999)),
                title=f"HN story {i + 1}: Ask HN about AI safety",
                created_utc=1_700_000_000 + i * 3600,
            )
            db.add(post)
            db.flush()
            posts.append(post)

        # 60 comments: 15 per stance, spread across the two posts
        for idx, stance in enumerate(_STANCES):
            # Each stance cluster has a distinct centroid region in embedding space
            centroid = np_rng.uniform(-1, 1, size=_EMBED_DIM).astype(np.float32)
            centroid /= np.linalg.norm(centroid)

            for j in range(_COMMENTS_PER_STANCE):
                post = posts[j % 2]
                comment = Comment(
                    topic_id=topic.id,
                    post_id=post.id,
                    external_id=str(rng.randint(10_000_000, 99_999_999)),
                    body=f"This is a {stance.lower()} comment number {j + 1}. "
                    f"It expresses a clear opinion on AI safety. " * 3,
                    author_hash=f"hash_{idx}_{j:04d}",
                    score=rng.randint(1, 100),
                    created_utc=1_700_000_000 + idx * 1000 + j * 60,
                )
                db.add(comment)
                db.flush()

                # Classification (bypasses ML models)
                clf = Classification(
                    comment_id=comment.id,
                    stance=stance,
                    sentiment="NEUTRAL",
                    toxicity_score=round(rng.uniform(0.0, 0.4), 3),
                )
                db.add(clf)
                db.flush()

                # Embedding — small perturbation around the stance centroid
                noise = np_rng.normal(0, 0.1, size=_EMBED_DIM).astype(np.float32)
                vec = centroid + noise
                emb = Embedding(
                    comment_id=comment.id,
                    embedding_vector=json.dumps(vec.tolist()),
                )
                db.add(emb)

        db.commit()
        topic_id = topic.id

    return topic_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestE2ESmokePipeline:
    def test_clustering_produces_clusters(self):
        topic_id = _seed_pipeline_data()

        with TestingSessionLocal() as db:
            result = run_clustering_for_topic(db, topic_id=topic_id)
            db.commit()

        assert result["topic_id"] == topic_id
        # At least one stance should have produced clusters
        total_clusters = sum(v["clusters"] for v in result["stances"].values())
        assert total_clusters >= 1

    def test_daily_stats_produces_rows(self):
        topic_id = _seed_pipeline_data()

        with TestingSessionLocal() as db:
            stats_result = run_daily_stats(db, topic_id=topic_id)
            db.commit()

        assert stats_result["topics_processed"] >= 1
        assert stats_result["rows_upserted"] >= 1

    def test_clusters_api_returns_clusters(self):
        topic_id = _seed_pipeline_data()

        # Run clustering so the DB has Cluster rows
        with TestingSessionLocal() as db:
            run_clustering_for_topic(db, topic_id=topic_id)
            db.commit()

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        # Success path returns 'clusters' list (no 'clustering_available' key)
        assert "clusters" in body
        assert len(body["clusters"]) >= 1

    def test_timeline_api_returns_entries_after_stats(self):
        topic_id = _seed_pipeline_data()

        # Run stats so the DB has DailyStats rows
        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)
            db.commit()

        resp = client.get(f"/api/timeline?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["topic_id"] == topic_id
        assert len(body["timeline"]) >= 1

    def test_full_pipeline_clusters_then_timeline(self):
        """Run the complete pipeline in order and assert both APIs return data."""
        topic_id = _seed_pipeline_data()

        with TestingSessionLocal() as db:
            run_clustering_for_topic(db, topic_id=topic_id)
            run_daily_stats(db, topic_id=topic_id)
            db.commit()

        clusters_resp = client.get(f"/api/clusters?topic_id={topic_id}")
        timeline_resp = client.get(f"/api/timeline?topic_id={topic_id}")

        assert clusters_resp.status_code == 200
        assert timeline_resp.status_code == 200
        assert "clusters" in clusters_resp.json()
        assert len(clusters_resp.json()["clusters"]) >= 1
        assert len(timeline_resp.json()["timeline"]) >= 1

    def test_stance_distribution_in_timeline(self):
        topic_id = _seed_pipeline_data()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)
            db.commit()

        resp = client.get(f"/api/timeline?topic_id={topic_id}")
        entries = resp.json()["timeline"]
        assert len(entries) >= 1

        # Percentages should sum to ~1.0 per row
        for entry in entries:
            total_pct = (
                entry["support_pct"]
                + entry["oppose_pct"]
                + entry["mixed_pct"]
                + entry["neutral_pct"]
            )
            if entry["total_comments"] > 0:
                assert abs(total_pct - 1.0) < 1e-5
