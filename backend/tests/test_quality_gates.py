"""Tests for Issue #29: Quality gates (min cluster size + clustering_available gate)."""

from __future__ import annotations

import os

import pytest
from unittest.mock import MagicMock, patch

import numpy as np

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_quality.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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
    # Re-assert the DB override in case another test module changed it
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_topic(db) -> Topic:
    t = Topic(name="QG Topic", description="")
    db.add(t)
    db.flush()
    return t


def _seed_post(db, topic_id: int) -> Post:
    import random

    p = Post(
        topic_id=topic_id,
        external_id=str(random.randint(10**6, 10**7)),
        title="Post",
        created_utc=1700000000,
    )
    db.add(p)
    db.flush()
    return p


def _seed_comment(db, topic_id: int, post_id: int) -> Comment:
    import random

    c = Comment(
        topic_id=topic_id,
        post_id=post_id,
        external_id=str(random.randint(10**6, 10**7)),
        body="x" * 60,
        author_hash="hash",
        score=1,
        created_utc=1700000000,
    )
    db.add(c)
    db.flush()
    return c


def _seed_classification(
    db, comment_id: int, stance: str = "SUPPORT"
) -> Classification:
    cl = Classification(comment_id=comment_id, stance=stance, sentiment="POSITIVE")
    db.add(cl)
    db.flush()
    return cl


# ---------------------------------------------------------------------------
# API quality gate tests
# ---------------------------------------------------------------------------


class TestClusteringAvailableGate:
    def test_returns_not_available_when_no_classifications(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["clustering_available"] is False
        assert body["topic_id"] == topic_id

    def test_returns_not_available_below_threshold(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            for _ in range(10):
                c = _seed_comment(db, topic.id, post.id)
                _seed_classification(db, c.id)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        assert resp.status_code == 200
        assert resp.json()["clustering_available"] is False

    def test_returns_clusters_when_above_threshold(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            post = _seed_post(db, topic.id)
            for _ in range(300):
                c = _seed_comment(db, topic.id, post.id)
                _seed_classification(db, c.id)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        # Should not have clustering_available=False
        assert "clusters" in body

    def test_not_available_response_includes_reason(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/clusters?topic_id={topic_id}")
        body = resp.json()
        assert "reason" in body
        assert "classified_comments" in body
        assert "required" in body


# ---------------------------------------------------------------------------
# Clusterer min_cluster_size gate tests
# ---------------------------------------------------------------------------


class TestMinClusterSizeGate:
    """Tests that clusters below min_cluster_size are pruned."""

    def _make_db_with_rows(self, n_comments: int):
        """Return a mock DB with n_comments rows for a single stance."""

        comments = []
        embeddings = []
        for i in range(1, n_comments + 1):
            c = MagicMock()
            c.id = i
            c.body = "x" * 60
            c.cluster_id = None
            comments.append(c)

            e = MagicMock()
            import json

            vec = [float(i)] * 384
            e.embedding_vector = json.dumps(vec)
            embeddings.append(e)

        rows = list(zip(comments, embeddings))

        db = MagicMock()
        db.execute.return_value.all.return_value = rows
        db.query.return_value.filter.return_value.all.return_value = []
        db.flush = MagicMock()
        db.commit = MagicMock()
        db.delete = MagicMock()

        return db, comments

    def test_small_cluster_deleted(self):
        """Clusters with size below min_cluster_size should be deleted."""
        from app.services.clusterer import run_clustering_for_topic
        from app.config import settings

        # 2 comments → 2 clusters of size 1 each → both below min_cluster_size=8
        db, comments = self._make_db_with_rows(2)

        km_mock = MagicMock()
        km_mock.fit_predict.return_value = np.array([0, 1])
        km_mock.cluster_centers_ = np.array([[1.0] * 384, [2.0] * 384])

        cluster_counter = [0]

        def add_side(obj):
            from app.models import Cluster as C

            if isinstance(obj, C):
                cluster_counter[0] += 1
                obj.id = cluster_counter[0]

        db.add.side_effect = add_side

        with patch("sklearn.cluster.KMeans", return_value=km_mock), patch.object(
            settings, "n_clusters_per_stance", 10
        ), patch.object(settings, "min_cluster_size", 8):
            run_clustering_for_topic(db, topic_id=1)

        # db.delete should be called (for the small clusters)
        assert db.delete.call_count > 0

    def test_large_cluster_not_deleted(self):
        """Clusters meeting min_cluster_size threshold should not be deleted."""
        from app.services.clusterer import run_clustering_for_topic
        from app.config import settings

        # 4 stances × 2 comments = we'll give all to one label so size=2
        # with min_cluster_size=2 (patched), cluster is kept
        db, _ = self._make_db_with_rows(4)

        km_mock = MagicMock()
        km_mock.fit_predict.return_value = np.array([0, 0, 0, 0])
        km_mock.cluster_centers_ = np.array([[1.0] * 384])

        cluster_counter = [0]

        def add_side(obj):
            from app.models import Cluster as C

            if isinstance(obj, C):
                cluster_counter[0] += 1
                obj.id = cluster_counter[0]

        db.add.side_effect = add_side

        with patch("sklearn.cluster.KMeans", return_value=km_mock), patch.object(
            settings, "n_clusters_per_stance", 1
        ), patch.object(settings, "min_cluster_size", 2):
            run_clustering_for_topic(db, topic_id=1)

        # delete should NOT be called for the 4-comment cluster (size=4 >= min=2)
        # (it may still be called for old clusters, but those are mocked as empty)
        # Verify no Cluster objects were passed to delete
        from app.models import Cluster as ClusterModel

        cluster_deletes = [
            c for c in db.delete.call_args_list if isinstance(c.args[0], ClusterModel)
        ]
        assert cluster_deletes == []
