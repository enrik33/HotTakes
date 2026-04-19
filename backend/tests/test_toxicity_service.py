"""
Tests for the toxicity scoring service (Issue #19).

All tests mock the HuggingFace pipeline so no model weights are downloaded.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.services.toxicity_service as svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_pipeline_output(label: str, score: float):
    """Return a callable that mimics pipe(text) -> [{"label": ..., "score": ...}]."""
    mock = MagicMock()
    mock.return_value = [{"label": label, "score": score}]
    return mock


# ---------------------------------------------------------------------------
# _extract_score — probability extraction and clamping
# ---------------------------------------------------------------------------


class TestExtractScore:
    def test_toxic_label_returns_score_directly(self):
        assert svc._extract_score({"label": "LABEL_1", "score": 0.9}) == pytest.approx(
            0.9
        )

    def test_toxic_label_variant(self):
        assert svc._extract_score({"label": "TOXIC", "score": 0.75}) == pytest.approx(
            0.75
        )

    def test_benign_label_returns_inverted_score(self):
        # LABEL_0 with score 0.8 means 80% chance of being benign → 20% toxic
        assert svc._extract_score({"label": "LABEL_0", "score": 0.8}) == pytest.approx(
            0.2
        )

    def test_score_clamped_to_one(self):
        # Edge case: model returns >1 due to floating-point errors
        assert svc._extract_score({"label": "LABEL_1", "score": 1.1}) == pytest.approx(
            1.0
        )

    def test_score_clamped_to_zero(self):
        assert svc._extract_score({"label": "LABEL_1", "score": -0.1}) == pytest.approx(
            0.0
        )

    def test_missing_label_defaults_to_benign_logic(self):
        # Empty label → treated as benign, so score is inverted
        result = svc._extract_score({"label": "", "score": 0.6})
        assert result == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# toxicity_bucket
# ---------------------------------------------------------------------------


class TestToxicityBucket:
    def test_below_low_threshold(self):
        assert svc.toxicity_bucket(0.0) == "low"
        assert svc.toxicity_bucket(0.1) == "low"
        assert svc.toxicity_bucket(0.29) == "low"

    def test_at_low_boundary_is_medium(self):
        assert svc.toxicity_bucket(0.3) == "medium"

    def test_medium_range(self):
        assert svc.toxicity_bucket(0.5) == "medium"
        assert svc.toxicity_bucket(0.69) == "medium"

    def test_at_high_boundary(self):
        assert svc.toxicity_bucket(0.7) == "high"

    def test_high_range(self):
        assert svc.toxicity_bucket(0.9) == "high"
        assert svc.toxicity_bucket(1.0) == "high"


# ---------------------------------------------------------------------------
# score_toxicity_batch
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    svc.reset_pipeline()
    yield
    svc.reset_pipeline()


class TestScoreToxicityBatch:
    def test_toxic_comment(self):
        mock_pipe = make_pipeline_output("LABEL_1", 0.95)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(["You're an idiot."])
        assert result == [pytest.approx(0.95)]

    def test_benign_comment(self):
        mock_pipe = make_pipeline_output("LABEL_0", 0.99)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(["Great work on this PR!"])
        # 1 - 0.99 = 0.01 toxic probability
        assert result == [pytest.approx(0.01)]

    def test_empty_string_scores_zero_without_pipeline(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch([""])
        mock_pipe.assert_not_called()
        assert result == [0.0]

    def test_whitespace_only_scores_zero(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(["   "])
        mock_pipe.assert_not_called()
        assert result == [0.0]

    def test_scores_are_clamped(self):
        mock_pipe = MagicMock(return_value=[{"label": "LABEL_1", "score": 1.5}])
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(["some text"])
        assert result == [pytest.approx(1.0)]

    def test_batch_preserves_order(self):
        outputs = [
            [{"label": "LABEL_1", "score": 0.9}],
            [{"label": "LABEL_0", "score": 0.95}],
            [{"label": "LABEL_1", "score": 0.5}],
        ]
        mock_pipe = MagicMock(side_effect=outputs)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(
                ["toxic", "benign", "midrange"], batch_size=32
            )
        assert result[0] == pytest.approx(0.9)
        assert result[1] == pytest.approx(0.05)  # 1 - 0.95
        assert result[2] == pytest.approx(0.5)

    def test_batch_chunking(self):
        mock_pipe = MagicMock(return_value=[{"label": "LABEL_0", "score": 0.99}])
        texts = ["text"] * 5
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(texts, batch_size=2)
        assert len(result) == 5

    def test_inference_error_defaults_to_zero(self):
        mock_pipe = MagicMock(side_effect=RuntimeError("model failure"))
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(["some comment"])
        assert result == [0.0]

    def test_error_on_one_item_does_not_abort_batch(self):
        outputs = [
            RuntimeError("boom"),
            [{"label": "LABEL_1", "score": 0.88}],
        ]
        mock_pipe = MagicMock(side_effect=outputs)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch(["bad", "fine"])
        assert result[0] == 0.0
        assert result[1] == pytest.approx(0.88)

    def test_empty_input_returns_empty(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.score_toxicity_batch([])
        assert result == []
