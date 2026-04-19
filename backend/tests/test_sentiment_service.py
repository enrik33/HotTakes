"""
Tests for the sentiment classification service (Issue #18).

All tests mock the HuggingFace pipeline so no model weights are downloaded.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.services.sentiment_service as svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_pipeline_mock(label: str, score: float):
    """Return a callable mock that mimics transformers.pipeline()(text)."""
    mock = MagicMock()
    mock.return_value = [{"label": label, "score": score}]
    return mock


# ---------------------------------------------------------------------------
# _map_output — label mapping
# ---------------------------------------------------------------------------


class TestMapOutput:
    def test_positive_high_confidence(self):
        assert svc._map_output("POSITIVE", 0.95) == "POSITIVE"

    def test_negative_high_confidence(self):
        assert svc._map_output("NEGATIVE", 0.90) == "NEGATIVE"

    def test_positive_low_confidence_becomes_neutral(self):
        assert svc._map_output("POSITIVE", 0.80) == "NEUTRAL"

    def test_negative_low_confidence_becomes_neutral(self):
        assert svc._map_output("NEGATIVE", 0.50) == "NEUTRAL"

    def test_exactly_at_threshold_is_not_neutral(self):
        # score == threshold should pass (>= check)
        assert svc._map_output("POSITIVE", 0.85) == "POSITIVE"

    def test_just_below_threshold_is_neutral(self):
        assert svc._map_output("NEGATIVE", 0.8499) == "NEUTRAL"

    def test_label_0_maps_to_negative(self):
        assert svc._map_output("LABEL_0", 0.99) == "NEGATIVE"

    def test_label_1_maps_to_positive(self):
        assert svc._map_output("LABEL_1", 0.99) == "POSITIVE"

    def test_unknown_label_maps_to_neutral(self):
        assert svc._map_output("WEIRD", 0.99) == "NEUTRAL"


# ---------------------------------------------------------------------------
# classify_sentiment_batch
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure the lazy-loaded pipeline singleton is cleared between tests."""
    svc.reset_pipeline()
    yield
    svc.reset_pipeline()


class TestClassifySentimentBatch:
    def test_single_positive_comment(self):
        mock_pipe = make_pipeline_mock("POSITIVE", 0.97)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(["This is amazing!"])
        assert result == ["POSITIVE"]

    def test_single_negative_comment(self):
        mock_pipe = make_pipeline_mock("NEGATIVE", 0.92)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(["Terrible product."])
        assert result == ["NEGATIVE"]

    def test_low_confidence_returns_neutral(self):
        mock_pipe = make_pipeline_mock("POSITIVE", 0.60)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(["Meh, it's okay I guess."])
        assert result == ["NEUTRAL"]

    def test_empty_string_returns_neutral_without_calling_pipeline(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch([""])
        mock_pipe.assert_not_called()
        assert result == ["NEUTRAL"]

    def test_whitespace_only_returns_neutral(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(["   "])
        mock_pipe.assert_not_called()
        assert result == ["NEUTRAL"]

    def test_batch_preserves_order(self):
        """Labels are returned in the same order as inputs."""
        outputs = [
            [{"label": "POSITIVE", "score": 0.95}],
            [{"label": "NEGATIVE", "score": 0.90}],
            [{"label": "POSITIVE", "score": 0.60}],  # low → NEUTRAL
        ]
        mock_pipe = MagicMock(side_effect=outputs)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(
                ["Great!", "Awful.", "Whatever."], batch_size=32
            )
        assert result == ["POSITIVE", "NEGATIVE", "NEUTRAL"]

    def test_batch_chunking(self):
        """With batch_size=2, a list of 5 texts is chunked correctly."""
        mock_pipe = MagicMock(return_value=[{"label": "POSITIVE", "score": 0.95}])
        texts = ["text"] * 5
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(texts, batch_size=2)
        assert len(result) == 5
        assert all(r == "POSITIVE" for r in result)

    def test_per_item_inference_error_returns_neutral(self):
        """An exception on one item is caught; that item gets NEUTRAL."""
        mock_pipe = MagicMock(side_effect=RuntimeError("model exploded"))
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(["Some comment."])
        assert result == ["NEUTRAL"]

    def test_error_on_one_item_does_not_abort_batch(self):
        """An error on item 1 should not prevent item 2 from being classified."""
        outputs = [
            RuntimeError("boom"),
            [{"label": "NEGATIVE", "score": 0.91}],
        ]
        mock_pipe = MagicMock(side_effect=outputs)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch(["bad text", "ok text"])
        assert result == ["NEUTRAL", "NEGATIVE"]

    def test_empty_input_returns_empty(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_sentiment_batch([])
        assert result == []
