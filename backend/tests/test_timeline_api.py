"""Tests for the timeline API route (Issue #38)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_timeline_api.db")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import DailyStats, Topic  # noqa: E402

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
    topic = Topic(name="Timeline Topic", description="desc")
    db.add(topic)
    db.flush()
    return topic


def _seed_daily_stat(
    db,
    topic_id: int,
    date: str,
    support: int = 5,
    oppose: int = 3,
    mixed: int = 1,
    neutral: int = 1,
    avg_toxicity: float = 0.15,
) -> DailyStats:
    stat = DailyStats(
        topic_id=topic_id,
        date=date,
        stance_support_count=support,
        stance_oppose_count=oppose,
        stance_mixed_count=mixed,
        stance_neutral_count=neutral,
        avg_toxicity_score=avg_toxicity,
        total_comments=support + oppose + mixed + neutral,
    )
    db.add(stat)
    db.flush()
    return stat


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestTimelineApiBasic:
    def test_missing_topic_id_returns_422(self):
        resp = client.get("/api/timeline")
        assert resp.status_code == 422

    def test_empty_topic_returns_empty_timeline(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/timeline?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["topic_id"] == topic_id
        assert body["timeline"] == []

    def test_unknown_topic_returns_empty_timeline(self):
        resp = client.get("/api/timeline?topic_id=99999")
        assert resp.status_code == 200
        body = resp.json()
        assert body["topic_id"] == 99999
        assert body["timeline"] == []

    def test_returns_seeded_stats(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_daily_stat(db, topic.id, "2026-04-01")
            _seed_daily_stat(db, topic.id, "2026-04-02")
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/timeline?topic_id={topic_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["timeline"]) == 2

    def test_timeline_entry_fields_present(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_daily_stat(db, topic.id, "2026-04-01", support=10, oppose=5)
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/timeline?topic_id={topic_id}")
        assert resp.status_code == 200
        entry = resp.json()["timeline"][0]
        assert "date" in entry
        assert "stance_support_count" in entry
        assert "stance_oppose_count" in entry
        assert "stance_mixed_count" in entry
        assert "stance_neutral_count" in entry
        assert "support_pct" in entry
        assert "oppose_pct" in entry
        assert "avg_toxicity" in entry
        assert "total_comments" in entry

    def test_percentages_sum_to_one(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_daily_stat(
                db, topic.id, "2026-04-01", support=5, oppose=3, mixed=1, neutral=1
            )
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/timeline?topic_id={topic_id}")
        entry = resp.json()["timeline"][0]
        total_pct = (
            entry["support_pct"]
            + entry["oppose_pct"]
            + entry["mixed_pct"]
            + entry["neutral_pct"]
        )
        assert abs(total_pct - 1.0) < 1e-6

    def test_timeline_ordered_by_date_ascending(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            # Seed out of order
            _seed_daily_stat(db, topic.id, "2026-04-03")
            _seed_daily_stat(db, topic.id, "2026-04-01")
            _seed_daily_stat(db, topic.id, "2026-04-02")
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/timeline?topic_id={topic_id}")
        dates = [e["date"] for e in resp.json()["timeline"]]
        assert dates == sorted(dates)


class TestTimelineApiFilters:
    def test_date_from_filter(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_daily_stat(db, topic.id, "2026-03-01")
            _seed_daily_stat(db, topic.id, "2026-04-01")
            _seed_daily_stat(db, topic.id, "2026-04-10")
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/timeline?topic_id={topic_id}&date_from=2026-04-01")
        assert resp.status_code == 200
        dates = [e["date"] for e in resp.json()["timeline"]]
        assert "2026-03-01" not in dates
        assert len(dates) == 2

    def test_date_to_filter(self):
        with TestingSessionLocal() as db:
            topic = _seed_topic(db)
            _seed_daily_stat(db, topic.id, "2026-04-01")
            _seed_daily_stat(db, topic.id, "2026-04-10")
            _seed_daily_stat(db, topic.id, "2026-04-20")
            db.commit()
            topic_id = topic.id

        resp = client.get(f"/api/timeline?topic_id={topic_id}&date_to=2026-04-10")
        assert resp.status_code == 200
        dates = [e["date"] for e in resp.json()["timeline"]]
        assert "2026-04-20" not in dates
        assert len(dates) == 2
