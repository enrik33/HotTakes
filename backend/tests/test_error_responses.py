import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

os.environ["REDDIT_CLIENT_ID"] = "test-id"
os.environ["REDDIT_CLIENT_SECRET"] = "test-secret"
os.environ["REDDIT_USER_AGENT"] = "test-agent"
os.environ["DATABASE_URL"] = "sqlite:///./test_errors.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "false"
os.environ["SCHEDULER_ENABLED"] = "false"

from app.database import Base, get_db
from app.main import app


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
client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)


def assert_error_shape(payload: dict):
    assert "error" in payload
    assert "request_id" in payload
    assert "code" in payload["error"]
    assert "message" in payload["error"]
    assert "details" in payload["error"]


def test_400_error_shape_for_duplicate_topic():
    topic = {"name": "Arsenal transfers", "description": "test"}
    first = client.post("/api/topics", json=topic)
    assert first.status_code == 200

    second = client.post("/api/topics", json=topic)
    assert second.status_code == 400
    body = second.json()
    assert_error_shape(body)
    assert body["error"]["code"] == "TOPIC_ALREADY_EXISTS"
    assert body["error"]["message"] == "Topic already exists"


def test_404_error_shape_for_missing_topic():
    response = client.get("/api/topics/99999")
    assert response.status_code == 404
    body = response.json()
    assert_error_shape(body)
    assert body["error"]["code"] == "TOPIC_NOT_FOUND"
    assert body["error"]["message"] == "Topic not found"


def test_422_error_shape_for_validation_error():
    response = client.get("/api/comments", params={"topic_id": 1, "limit": 0})
    assert response.status_code == 422
    body = response.json()
    assert_error_shape(body)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Validation error"
    assert isinstance(body["error"]["details"], list)


def test_500_error_shape_for_unhandled_exception():
    original_override = app.dependency_overrides[get_db]

    def broken_db():
        raise RuntimeError("forced db failure")

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/api/topics")
    finally:
        app.dependency_overrides[get_db] = original_override

    assert response.status_code == 500
    body = response.json()
    assert_error_shape(body)
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "Internal server error"
