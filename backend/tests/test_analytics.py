"""Tests for analytics.py (Issue #30) — daily stats aggregation."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_analytics.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from app.database import Base  # noqa: E402
from app.models import Classification, Comment, DailyStats, Post, Topic  # noqa: E402
from app.services.analytics import run_daily_stats  # noqa: E402

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UNIX_2024_01_01 = 1704067200  # 2024-01-01 00:00:00 UTC


def _seed(
    db,
    topic_id: int,
    post_id: int,
    stance: str,
    toxicity: float | None = None,
    created_utc: int = _UNIX_2024_01_01,
):
    import random

    c = Comment(
        topic_id=topic_id,
        post_id=post_id,
        external_id=str(random.randint(10**6, 10**7)),
        body="x" * 60,
        author_hash="h",
        score=1,
        created_utc=created_utc,
    )
    db.add(c)
    db.flush()
    cl = Classification(
        comment_id=c.id,
        stance=stance,
        sentiment="POSITIVE",
        toxicity_score=toxicity,
    )
    db.add(cl)
    db.flush()
    return c, cl


def _setup_topic(db) -> tuple[int, int]:
    t = Topic(name="Stats Topic", description="")
    db.add(t)
    db.flush()
    p = Post(
        topic_id=t.id,
        external_id="123",
        title="P",
        created_utc=_UNIX_2024_01_01,
    )
    db.add(p)
    db.flush()
    return t.id, p.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRunDailyStatsBasic:
    def test_no_comments_returns_zero_upserted(self):
        with TestingSessionLocal() as db:
            topic_id, _ = _setup_topic(db)
            db.commit()

        with TestingSessionLocal() as db:
            result = run_daily_stats(db, topic_id=topic_id)

        assert result["topics_processed"] == 1
        assert result["rows_upserted"] == 0

    def test_single_comment_creates_one_row(self):
        with TestingSessionLocal() as db:
            topic_id, post_id = _setup_topic(db)
            _seed(db, topic_id, post_id, "SUPPORT")
            db.commit()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)

        with TestingSessionLocal() as db:
            rows = db.query(DailyStats).filter(DailyStats.topic_id == topic_id).all()
        assert len(rows) == 1

    def test_stance_count_correct(self):
        with TestingSessionLocal() as db:
            topic_id, post_id = _setup_topic(db)
            _seed(db, topic_id, post_id, "SUPPORT")
            _seed(db, topic_id, post_id, "SUPPORT")
            _seed(db, topic_id, post_id, "OPPOSE")
            db.commit()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)

        with TestingSessionLocal() as db:
            row = db.query(DailyStats).filter(DailyStats.topic_id == topic_id).first()
        assert row.stance_support_count == 2
        assert row.stance_oppose_count == 1
        assert row.stance_mixed_count == 0
        assert row.total_comments == 3

    def test_toxicity_average_computed(self):
        with TestingSessionLocal() as db:
            topic_id, post_id = _setup_topic(db)
            _seed(db, topic_id, post_id, "SUPPORT", toxicity=0.2)
            _seed(db, topic_id, post_id, "OPPOSE", toxicity=0.4)
            db.commit()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)

        with TestingSessionLocal() as db:
            row = db.query(DailyStats).filter(DailyStats.topic_id == topic_id).first()
        # (0.2 + 0.4) / 2 = 0.3
        assert abs(row.avg_toxicity_score - 0.3) < 0.01

    def test_null_toxicity_handled(self):
        with TestingSessionLocal() as db:
            topic_id, post_id = _setup_topic(db)
            _seed(db, topic_id, post_id, "NEUTRAL", toxicity=None)
            db.commit()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)

        with TestingSessionLocal() as db:
            row = db.query(DailyStats).filter(DailyStats.topic_id == topic_id).first()
        assert row.avg_toxicity_score is None

    def test_two_dates_creates_two_rows(self):
        _UNIX_2024_01_02 = _UNIX_2024_01_01 + 86400
        with TestingSessionLocal() as db:
            topic_id, post_id = _setup_topic(db)
            _seed(db, topic_id, post_id, "SUPPORT", created_utc=_UNIX_2024_01_01)
            _seed(db, topic_id, post_id, "OPPOSE", created_utc=_UNIX_2024_01_02)
            db.commit()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)

        with TestingSessionLocal() as db:
            rows = db.query(DailyStats).filter(DailyStats.topic_id == topic_id).all()
        assert len(rows) == 2

    def test_upsert_updates_existing_row(self):
        with TestingSessionLocal() as db:
            topic_id, post_id = _setup_topic(db)
            _seed(db, topic_id, post_id, "SUPPORT")
            db.commit()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)

        # Add more comments and run again
        with TestingSessionLocal() as db:

            p_id = post_id
            _seed(db, topic_id, p_id, "OPPOSE")
            db.commit()

        with TestingSessionLocal() as db:
            run_daily_stats(db, topic_id=topic_id)

        with TestingSessionLocal() as db:
            rows = db.query(DailyStats).filter(DailyStats.topic_id == topic_id).all()
        # Should still be just 1 row (same date), updated
        assert len(rows) == 1
        assert rows[0].total_comments == 2

    def test_commit_called(self):

        with TestingSessionLocal() as db:
            topic_id, post_id = _setup_topic(db)
            db.commit()

        with TestingSessionLocal() as db:
            original_commit = db.commit
            commit_called = [False]

            def track_commit():
                commit_called[0] = True
                original_commit()

            db.commit = track_commit
            run_daily_stats(db, topic_id=topic_id)

        assert commit_called[0]


class TestRunDailyStatsAllTopics:
    def test_none_topic_id_processes_all_active_topics(self):
        with TestingSessionLocal() as db:
            t1 = Topic(name="Active1", description="", status="active")
            t2 = Topic(name="Active2", description="", status="active")
            t3 = Topic(name="Archived", description="", status="archived")
            db.add_all([t1, t2, t3])
            db.flush()
            for t in [t1, t2]:
                p = Post(
                    topic_id=t.id,
                    external_id=f"p{t.id}",
                    title="P",
                    created_utc=_UNIX_2024_01_01,
                )
                db.add(p)
                db.flush()
                _seed(db, t.id, p.id, "SUPPORT")
            db.commit()

        with TestingSessionLocal() as db:
            result = run_daily_stats(db, topic_id=None)

        assert result["topics_processed"] == 2
        assert result["rows_upserted"] == 2

    def test_archived_topic_skipped(self):
        with TestingSessionLocal() as db:
            t = Topic(name="Archived2", description="", status="archived")
            db.add(t)
            db.flush()
            p = Post(
                topic_id=t.id,
                external_id="p99",
                title="P",
                created_utc=_UNIX_2024_01_01,
            )
            db.add(p)
            db.flush()
            _seed(db, t.id, p.id, "SUPPORT")
            db.commit()

        with TestingSessionLocal() as db:
            result = run_daily_stats(db, topic_id=None)

        assert result["topics_processed"] == 0
        assert result["rows_upserted"] == 0
