"""
Tests for classify_job.run_classify_job (Issue #23).

All DB access and ML services are mocked — no real database or model weights needed.
"""

from __future__ import annotations

import os

# Must be set before any app imports to prevent app.database from trying to
# connect to PostgreSQL (which is not available in the local dev environment).
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ENVIRONMENT", "development")

from unittest.mock import MagicMock, patch


from app.tasks.classify_job import run_classify_job


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_comment(
    id: int,
    body: str = "Some comment body",
    target_terms: str = "OpenAI",
) -> MagicMock:
    post = MagicMock()
    post.target_terms = target_terms
    comment = MagicMock()
    comment.id = id
    comment.body = body
    comment.post = post
    return comment


def _make_db(comments: list) -> MagicMock:
    """Return a mock Session whose execute().scalars().unique() yields *comments*."""
    scalars = MagicMock()
    scalars.unique.return_value = iter(comments)
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars
    db = MagicMock()
    db.execute.return_value = execute_result
    return db


# ---------------------------------------------------------------------------
# No pending comments
# ---------------------------------------------------------------------------


class TestNoPendingComments:
    def test_returns_zeros_when_no_comments(self):
        db = _make_db([])
        result = run_classify_job(db)
        assert result == {"classified": 0, "gated": 0, "errors": 0}

    def test_commit_not_called_when_nothing_to_do(self):
        db = _make_db([])
        run_classify_job(db)
        db.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Stance gating path
# ---------------------------------------------------------------------------


class TestStanceGating:
    def test_off_topic_comment_is_gated(self):
        comment = _make_comment(
            1, body="The weather is nice today.", target_terms="OpenAI"
        )

        with (
            patch("app.tasks.classify_job.is_on_target", return_value=False),
            patch("app.tasks.classify_job.split_target_terms", return_value=["OpenAI"]),
            patch("app.tasks.classify_job.classify_sentiment_batch") as mock_sent,
            patch("app.tasks.classify_job.score_toxicity_batch") as mock_tox,
            patch("app.tasks.classify_job.classify_stance_batch") as mock_stance,
        ):
            db = _make_db([comment])
            result = run_classify_job(db)

        # ML classifiers should NOT be called for a gated comment
        mock_sent.assert_not_called()
        mock_tox.assert_not_called()
        mock_stance.assert_not_called()

        assert result["gated"] == 1
        assert result["classified"] == 0
        assert result["errors"] == 0

    def test_gated_classification_written_as_rule(self):
        comment = _make_comment(1, body="off-topic", target_terms="Tesla")

        added_objects = []
        db = _make_db([comment])
        db.add.side_effect = added_objects.append

        with (
            patch("app.tasks.classify_job.is_on_target", return_value=False),
            patch("app.tasks.classify_job.split_target_terms", return_value=["Tesla"]),
        ):
            run_classify_job(db)

        assert len(added_objects) == 1
        cls = added_objects[0]
        assert cls.comment_id == 1
        assert cls.stance == "NEUTRAL"
        assert cls.sentiment == "NEUTRAL"
        assert cls.toxicity_score == 0.0
        assert cls.classified_by == "rule"

    def test_no_target_terms_goes_to_model(self):
        comment = _make_comment(1, target_terms=None)
        comment.post.target_terms = None

        with (
            patch("app.tasks.classify_job.split_target_terms", return_value=[]),
            patch("app.tasks.classify_job.is_on_target") as mock_gate,
            patch(
                "app.tasks.classify_job.classify_sentiment_batch",
                return_value=["NEUTRAL"],
            ),
            patch("app.tasks.classify_job.score_toxicity_batch", return_value=[0.1]),
            patch(
                "app.tasks.classify_job.classify_stance_batch", return_value=["SUPPORT"]
            ),
        ):
            db = _make_db([comment])
            result = run_classify_job(db)

        # is_on_target should not be called when target_terms is empty
        mock_gate.assert_not_called()
        assert result["classified"] == 1
        assert result["gated"] == 0


# ---------------------------------------------------------------------------
# Model classification path
# ---------------------------------------------------------------------------


class TestModelPath:
    def test_classified_comment_gets_correct_row(self):
        comment = _make_comment(1, body="I love this product!", target_terms="OpenAI")

        added_objects = []
        db = _make_db([comment])
        db.add.side_effect = added_objects.append

        with (
            patch("app.tasks.classify_job.split_target_terms", return_value=["OpenAI"]),
            patch("app.tasks.classify_job.is_on_target", return_value=True),
            patch(
                "app.tasks.classify_job.classify_sentiment_batch",
                return_value=["POSITIVE"],
            ),
            patch("app.tasks.classify_job.score_toxicity_batch", return_value=[0.05]),
            patch(
                "app.tasks.classify_job.classify_stance_batch", return_value=["SUPPORT"]
            ),
        ):
            result = run_classify_job(db)

        assert result == {"classified": 1, "gated": 0, "errors": 0}
        assert len(added_objects) == 1
        cls = added_objects[0]
        assert cls.comment_id == 1
        assert cls.stance == "SUPPORT"
        assert cls.sentiment == "POSITIVE"
        assert cls.toxicity_score == 0.05
        assert cls.classified_by == "model"

    def test_multiple_comments_batched_correctly(self):
        comments = [_make_comment(i, target_terms="X") for i in range(1, 4)]

        with (
            patch("app.tasks.classify_job.split_target_terms", return_value=["X"]),
            patch("app.tasks.classify_job.is_on_target", return_value=True),
            patch(
                "app.tasks.classify_job.classify_sentiment_batch",
                return_value=["POSITIVE", "NEGATIVE", "NEUTRAL"],
            ),
            patch(
                "app.tasks.classify_job.score_toxicity_batch",
                return_value=[0.1, 0.2, 0.3],
            ),
            patch(
                "app.tasks.classify_job.classify_stance_batch",
                side_effect=[["SUPPORT"], ["OPPOSE"], ["MIXED"]],
            ),
        ):
            db = _make_db(comments)
            result = run_classify_job(db)

        assert result["classified"] == 3

    def test_commit_called_after_writes(self):
        comment = _make_comment(1, target_terms="Y")

        with (
            patch("app.tasks.classify_job.split_target_terms", return_value=["Y"]),
            patch("app.tasks.classify_job.is_on_target", return_value=True),
            patch(
                "app.tasks.classify_job.classify_sentiment_batch",
                return_value=["NEUTRAL"],
            ),
            patch("app.tasks.classify_job.score_toxicity_batch", return_value=[0.0]),
            patch(
                "app.tasks.classify_job.classify_stance_batch", return_value=["NEUTRAL"]
            ),
        ):
            db = _make_db([comment])
            run_classify_job(db)

        db.commit.assert_called_once()


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    def test_stance_inference_error_defaults_to_neutral_and_still_writes(self):
        comment = _make_comment(1, target_terms="Z")

        added_objects = []
        db = _make_db([comment])
        db.add.side_effect = added_objects.append

        with (
            patch("app.tasks.classify_job.split_target_terms", return_value=["Z"]),
            patch("app.tasks.classify_job.is_on_target", return_value=True),
            patch(
                "app.tasks.classify_job.classify_sentiment_batch",
                return_value=["POSITIVE"],
            ),
            patch("app.tasks.classify_job.score_toxicity_batch", return_value=[0.1]),
            patch(
                "app.tasks.classify_job.classify_stance_batch",
                side_effect=RuntimeError("NLI boom"),
            ),
        ):
            result = run_classify_job(db)

        # Comment should still be written with NEUTRAL stance fallback
        assert result["classified"] == 1
        assert result["errors"] == 0
        assert added_objects[0].stance == "NEUTRAL"

    def test_sentiment_batch_error_defaults_to_neutral(self):
        comment = _make_comment(1, target_terms="A")

        added_objects = []
        db = _make_db([comment])
        db.add.side_effect = added_objects.append

        with (
            patch("app.tasks.classify_job.split_target_terms", return_value=["A"]),
            patch("app.tasks.classify_job.is_on_target", return_value=True),
            patch(
                "app.tasks.classify_job.classify_sentiment_batch",
                side_effect=RuntimeError("boom"),
            ),
            patch("app.tasks.classify_job.score_toxicity_batch", return_value=[0.0]),
            patch(
                "app.tasks.classify_job.classify_stance_batch", return_value=["SUPPORT"]
            ),
        ):
            result = run_classify_job(db)

        assert result["classified"] == 1
        assert added_objects[0].sentiment == "NEUTRAL"

    def test_toxicity_batch_error_defaults_to_zero(self):
        comment = _make_comment(1, target_terms="B")

        added_objects = []
        db = _make_db([comment])
        db.add.side_effect = added_objects.append

        with (
            patch("app.tasks.classify_job.split_target_terms", return_value=["B"]),
            patch("app.tasks.classify_job.is_on_target", return_value=True),
            patch(
                "app.tasks.classify_job.classify_sentiment_batch",
                return_value=["NEUTRAL"],
            ),
            patch(
                "app.tasks.classify_job.score_toxicity_batch",
                side_effect=RuntimeError("tox boom"),
            ),
            patch(
                "app.tasks.classify_job.classify_stance_batch", return_value=["NEUTRAL"]
            ),
        ):
            result = run_classify_job(db)

        assert result["classified"] == 1
        assert added_objects[0].toxicity_score == 0.0
