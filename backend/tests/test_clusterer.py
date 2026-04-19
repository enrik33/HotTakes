"""
Tests for the stance-bucket clustering service (Issue #25).

All DB interactions are mocked — no real PostgreSQL or KMeans weights required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

import app.services.clusterer as svc
from app.services.clusterer import run_clustering_for_topic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_comment(id: int, cluster_id=None):
    c = MagicMock()
    c.id = id
    c.cluster_id = cluster_id
    c.body = f"This is a sample comment body for comment number {id} used in testing."
    return c


def _make_embedding(comment_id: int, vector=None):
    e = MagicMock()
    e.comment_id = comment_id
    if vector is None:
        vector = [float(comment_id)] * 384
    e.embedding_vector = __import__("json").dumps(vector)
    return e


def _make_db(rows=None, old_clusters=None):
    """Return a mock Session.

    rows      — list of (Comment, Embedding) tuples returned by execute().all()
    old_clusters — list of Cluster mocks returned by query().filter().all()
    """
    execute_result = MagicMock()
    execute_result.all.return_value = rows or []

    db = MagicMock()
    db.execute.return_value = execute_result

    # query(...).filter(...).all() chain for old clusters
    filter_mock = MagicMock()
    filter_mock.all.return_value = old_clusters or []
    query_mock = MagicMock()
    query_mock.filter.return_value = filter_mock
    db.query.return_value = query_mock

    return db


def _make_kmeans_mock(n_samples, n_clusters):
    """Return a KMeans mock that assigns label i % n_clusters to sample i."""
    labels = np.array([i % n_clusters for i in range(n_samples)])
    km = MagicMock()
    km.fit_predict.return_value = labels
    return km


# ---------------------------------------------------------------------------
# Tests: skip when < 2 samples
# ---------------------------------------------------------------------------


class TestSkipInsufficientSamples:
    def test_zero_comments_returns_zero_clusters(self):
        db = _make_db(rows=[])
        result = run_clustering_for_topic(db, topic_id=1)
        for stance_result in result["stances"].values():
            assert stance_result["clusters"] == 0

    def test_one_comment_returns_zero_clusters(self):
        c = _make_comment(1)
        e = _make_embedding(1)
        db = _make_db(rows=[(c, e)])
        result = run_clustering_for_topic(db, topic_id=1)
        for stance_result in result["stances"].values():
            assert stance_result["clusters"] == 0

    def test_commit_still_called_when_all_stances_skipped(self):
        db = _make_db(rows=[])
        run_clustering_for_topic(db, topic_id=1)
        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: clustering produces correct clusters
# ---------------------------------------------------------------------------


class TestClusteringOutput:
    def _run_with_n_comments(self, n, n_clusters_setting=10):
        comments = [_make_comment(i) for i in range(1, n + 1)]
        embeddings = [_make_embedding(i) for i in range(1, n + 1)]
        rows = list(zip(comments, embeddings))
        db = _make_db(rows=rows, old_clusters=[])

        expected_n_clusters = min(n_clusters_setting, n)
        km_mock = _make_kmeans_mock(n, expected_n_clusters)

        with patch("sklearn.cluster.KMeans", return_value=km_mock), patch.object(
            svc.settings, "n_clusters_per_stance", n_clusters_setting
        ), patch.object(svc.settings, "min_cluster_size", 1):
            result = run_clustering_for_topic(db, topic_id=1)

        return result, db, km_mock

    def test_two_comments_produce_two_clusters(self):
        result, db, _ = self._run_with_n_comments(2, n_clusters_setting=10)
        for stance_result in result["stances"].values():
            assert stance_result["clusters"] == 2
            assert stance_result["comments"] == 2

    def test_n_clusters_capped_at_n_samples(self):
        # 3 samples, setting=10 → should produce 3 clusters
        result, db, km = self._run_with_n_comments(3, n_clusters_setting=10)
        # fit_predict is called once per stance (4 stances)
        assert km.fit_predict.call_count == 4
        for stance_result in result["stances"].values():
            assert stance_result["clusters"] == 3

    def test_n_clusters_capped_at_setting(self):
        # 20 samples, setting=5 → should produce 5 clusters
        result, db, km = self._run_with_n_comments(20, n_clusters_setting=5)
        for stance_result in result["stances"].values():
            assert stance_result["clusters"] == 5

    def test_cluster_rows_added_to_db(self):
        comments = [_make_comment(i) for i in range(1, 3)]
        embeddings = [_make_embedding(i) for i in range(1, 3)]
        rows = list(zip(comments, embeddings))
        db = _make_db(rows=rows, old_clusters=[])

        km_mock = _make_kmeans_mock(2, 2)
        with patch("sklearn.cluster.KMeans", return_value=km_mock), patch.object(
            svc.settings, "min_cluster_size", 1
        ):
            run_clustering_for_topic(db, topic_id=1)

        # db.add should have been called for each of the 4 stances × 2 clusters
        assert db.add.call_count == 4 * 2  # 4 stances × 2 clusters each

    def test_comment_cluster_id_updated(self):
        from app.models import Cluster as ClusterModel  # noqa: PLC0415

        comments = [_make_comment(i) for i in range(1, 3)]
        embeddings = [_make_embedding(i) for i in range(1, 3)]
        rows = list(zip(comments, embeddings))
        db = _make_db(rows=rows, old_clusters=[])

        # Simulate DB auto-assigning IDs on flush by assigning in add()
        _counter = [0]

        def _add_side(obj):
            if isinstance(obj, ClusterModel) and obj.id is None:
                _counter[0] += 1
                obj.id = _counter[0]

        db.add.side_effect = _add_side

        km_mock = _make_kmeans_mock(2, 2)
        with patch("sklearn.cluster.KMeans", return_value=km_mock), patch.object(
            svc.settings, "min_cluster_size", 1
        ):
            run_clustering_for_topic(db, topic_id=1)

        # Each comment should have had cluster_id assigned (not None)
        for comment in comments:
            assert comment.cluster_id is not None

    def test_commit_called_once(self):
        comments = [_make_comment(i) for i in range(1, 3)]
        embeddings = [_make_embedding(i) for i in range(1, 3)]
        rows = list(zip(comments, embeddings))
        db = _make_db(rows=rows, old_clusters=[])

        km_mock = _make_kmeans_mock(2, 2)
        with patch("sklearn.cluster.KMeans", return_value=km_mock), patch.object(
            svc.settings, "min_cluster_size", 1
        ):
            run_clustering_for_topic(db, topic_id=1)

        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: old clusters are deleted
# ---------------------------------------------------------------------------


class TestOldClusterDeletion:
    def test_old_clusters_deleted_before_new_ones_inserted(self):
        comments = [_make_comment(i) for i in range(1, 3)]
        embeddings = [_make_embedding(i) for i in range(1, 3)]
        rows = list(zip(comments, embeddings))

        old_cluster = MagicMock()
        old_cluster.id = 99
        db = _make_db(rows=rows, old_clusters=[old_cluster])

        km_mock = _make_kmeans_mock(2, 2)
        with patch("sklearn.cluster.KMeans", return_value=km_mock), patch.object(
            svc.settings, "min_cluster_size", 1
        ):
            run_clustering_for_topic(db, topic_id=1)

        db.delete.assert_called_with(old_cluster)

    def test_topic_id_in_result(self):
        db = _make_db(rows=[])
        result = run_clustering_for_topic(db, topic_id=42)
        assert result["topic_id"] == 42


# ---------------------------------------------------------------------------
# Tests: stance separation
# ---------------------------------------------------------------------------


class TestStanceSeparation:
    def test_all_four_stances_in_result(self):
        db = _make_db(rows=[])
        result = run_clustering_for_topic(db, topic_id=1)
        assert set(result["stances"].keys()) == {
            "SUPPORT",
            "OPPOSE",
            "MIXED",
            "NEUTRAL",
        }
