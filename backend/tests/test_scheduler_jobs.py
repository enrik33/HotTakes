"""Tests for Issue #31: wired cluster_arguments and compute_daily_stats jobs."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_jobs.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from app.tasks.scheduler import cluster_arguments, compute_daily_stats


class TestClusterArgumentsJob:
    def test_calls_run_clustering_for_each_active_topic(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = [(5,), (6,)]
        mock_db.close = MagicMock()
        mock_fn = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_db):
            import app.services.clusterer as m

            orig = m.run_clustering_for_topic
            m.run_clustering_for_topic = mock_fn
            try:
                cluster_arguments()
            finally:
                m.run_clustering_for_topic = orig
        mock_fn.assert_any_call(mock_db, topic_id=5)
        mock_fn.assert_any_call(mock_db, topic_id=6)
        assert mock_fn.call_count == 2

    def test_db_closed_after_job(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = []
        mock_db.close = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_db):
            import app.services.clusterer as m

            orig = m.run_clustering_for_topic
            m.run_clustering_for_topic = MagicMock()
            try:
                cluster_arguments()
            finally:
                m.run_clustering_for_topic = orig
        mock_db.close.assert_called_once()

    def test_no_active_topics_does_not_call_clusterer(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.all.return_value = []
        mock_db.close = MagicMock()
        mock_fn = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_db):
            import app.services.clusterer as m

            orig = m.run_clustering_for_topic
            m.run_clustering_for_topic = mock_fn
            try:
                cluster_arguments()
            finally:
                m.run_clustering_for_topic = orig
        mock_fn.assert_not_called()


class TestComputeDailyStatsJob:
    def test_calls_run_daily_stats_with_none(self):
        mock_db = MagicMock()
        mock_db.close = MagicMock()
        mock_fn = MagicMock(return_value={"topics_processed": 0, "rows_upserted": 0})
        with patch("app.database.SessionLocal", return_value=mock_db):
            import app.services.analytics as m

            orig = m.run_daily_stats
            m.run_daily_stats = mock_fn
            try:
                compute_daily_stats()
            finally:
                m.run_daily_stats = orig
        mock_fn.assert_called_once_with(mock_db, topic_id=None)

    def test_db_closed_after_stats_job(self):
        mock_db = MagicMock()
        mock_db.close = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_db):
            import app.services.analytics as m

            orig = m.run_daily_stats
            m.run_daily_stats = MagicMock(
                return_value={"topics_processed": 0, "rows_upserted": 0}
            )
            try:
                compute_daily_stats()
            finally:
                m.run_daily_stats = orig
        mock_db.close.assert_called_once()

    def test_stats_job_exception_propagates_after_db_close(self):
        mock_db = MagicMock()
        mock_db.close = MagicMock()
        with patch("app.database.SessionLocal", return_value=mock_db):
            import app.services.analytics as m

            orig = m.run_daily_stats
            m.run_daily_stats = MagicMock(side_effect=RuntimeError("boom"))
            try:
                with pytest.raises(RuntimeError, match="boom"):
                    compute_daily_stats()
            finally:
                m.run_daily_stats = orig
        mock_db.close.assert_called_once()
