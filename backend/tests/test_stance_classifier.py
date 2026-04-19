"""
Tests for the stance classifier service (Issue #20).

All tests mock the HuggingFace pipeline — no model weights required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import app.services.stance_classifier as svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_zsc_output(top_label: str):
    """Return a mock pipeline that produces a zero-shot classification result.

    ``top_label`` must be a substring that appears in one of the hypothesis
    templates so that ``_top_label()`` can map it correctly.
    Examples: "supports", "opposes", "mixed", "unrelated"
    """
    mock = MagicMock()
    mock.return_value = {
        "labels": [top_label, "other1", "other2", "other3"],
        "scores": [0.8, 0.1, 0.05, 0.05],
    }
    return mock


# ---------------------------------------------------------------------------
# _build_candidate_labels
# ---------------------------------------------------------------------------


class TestBuildCandidateLabels:
    def test_with_target_includes_entity_name(self):
        labels = svc._build_candidate_labels(["GPT-4"])
        assert any("GPT-4" in lbl for lbl in labels)

    def test_with_empty_targets_uses_generic(self):
        labels = svc._build_candidate_labels([])
        assert all("GPT-4" not in lbl for lbl in labels)
        assert len(labels) == 4

    def test_uses_only_first_target(self):
        labels = svc._build_candidate_labels(["Claude", "OpenAI"])
        assert any("Claude" in lbl for lbl in labels)
        assert not any("OpenAI" in lbl for lbl in labels)

    def test_always_four_labels(self):
        assert len(svc._build_candidate_labels(["X"])) == 4
        assert len(svc._build_candidate_labels([])) == 4


# ---------------------------------------------------------------------------
# _top_label
# ---------------------------------------------------------------------------


class TestTopLabel:
    def _make_result(self, top_hypothesis: str) -> dict:
        return {
            "labels": [top_hypothesis, "other"],
            "scores": [0.9, 0.1],
        }

    def test_supports_maps_to_support(self):
        result = self._make_result("This comment supports GPT-4.")
        assert svc._top_label(result) == "SUPPORT"

    def test_opposes_maps_to_oppose(self):
        result = self._make_result("This comment opposes GPT-4.")
        assert svc._top_label(result) == "OPPOSE"

    def test_mixed_maps_to_mixed(self):
        result = self._make_result("This comment has a mixed opinion about GPT-4.")
        assert svc._top_label(result) == "MIXED"

    def test_unrelated_maps_to_neutral(self):
        result = self._make_result("This comment is unrelated to GPT-4.")
        assert svc._top_label(result) == "NEUTRAL"


# ---------------------------------------------------------------------------
# classify_stance_batch
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    svc.reset_pipeline()
    yield
    svc.reset_pipeline()


class TestClassifyStanceBatch:
    def test_support_label(self):
        mock_pipe = MagicMock(
            return_value={
                "labels": ["This comment supports GPT-4.", "a", "b", "c"],
                "scores": [0.8, 0.1, 0.05, 0.05],
            }
        )
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(
                ["GPT-4 is amazing!"], target_terms=["GPT-4"]
            )
        assert result == ["SUPPORT"]

    def test_oppose_label(self):
        mock_pipe = MagicMock(
            return_value={
                "labels": ["This comment opposes the main subject.", "a", "b", "c"],
                "scores": [0.9, 0.05, 0.03, 0.02],
            }
        )
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(["This is terrible."], target_terms=[])
        assert result == ["OPPOSE"]

    def test_mixed_label(self):
        mock_pipe = MagicMock(
            return_value={
                "labels": [
                    "This comment has a mixed opinion about Claude.",
                    "a",
                    "b",
                    "c",
                ],
                "scores": [0.7, 0.15, 0.1, 0.05],
            }
        )
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(
                ["Has some pros and cons."], target_terms=["Claude"]
            )
        assert result == ["MIXED"]

    def test_neutral_label_when_unrelated(self):
        mock_pipe = MagicMock(
            return_value={
                "labels": ["This comment is unrelated to OpenAI.", "a", "b", "c"],
                "scores": [0.85, 0.08, 0.04, 0.03],
            }
        )
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(
                ["Today is sunny."], target_terms=["OpenAI"]
            )
        assert result == ["NEUTRAL"]

    def test_empty_string_returns_neutral_without_pipeline_call(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch([""], target_terms=["X"])
        mock_pipe.assert_not_called()
        assert result == ["NEUTRAL"]

    def test_whitespace_only_returns_neutral(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(["   "], target_terms=[])
        mock_pipe.assert_not_called()
        assert result == ["NEUTRAL"]

    def test_empty_target_terms_still_classifies(self):
        mock_pipe = MagicMock(
            return_value={
                "labels": ["This comment supports the main subject.", "a", "b", "c"],
                "scores": [0.8, 0.1, 0.05, 0.05],
            }
        )
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(["I agree!"], target_terms=[])
        assert result == ["SUPPORT"]

    def test_batch_preserves_order(self):
        outputs = [
            {
                "labels": ["This comment supports GPT-4.", "a", "b", "c"],
                "scores": [0.9, 0.05, 0.03, 0.02],
            },
            {
                "labels": ["This comment opposes GPT-4.", "a", "b", "c"],
                "scores": [0.85, 0.1, 0.03, 0.02],
            },
        ]
        mock_pipe = MagicMock(side_effect=outputs)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(
                ["Love it", "Hate it"], target_terms=["GPT-4"]
            )
        assert result == ["SUPPORT", "OPPOSE"]

    def test_batch_chunking(self):
        mock_pipe = MagicMock(
            return_value={
                "labels": ["This comment supports X.", "a", "b", "c"],
                "scores": [0.8, 0.1, 0.05, 0.05],
            }
        )
        texts = ["text"] * 5
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(texts, target_terms=["X"], batch_size=2)
        assert len(result) == 5

    def test_inference_error_defaults_to_neutral(self):
        mock_pipe = MagicMock(side_effect=RuntimeError("NLI exploded"))
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(["something"], target_terms=["Y"])
        assert result == ["NEUTRAL"]

    def test_error_on_one_item_does_not_abort_batch(self):
        outputs = [
            RuntimeError("boom"),
            {
                "labels": ["This comment opposes Z.", "a", "b", "c"],
                "scores": [0.9, 0.05, 0.03, 0.02],
            },
        ]
        mock_pipe = MagicMock(side_effect=outputs)
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch(["bad", "good"], target_terms=["Z"])
        assert result[0] == "NEUTRAL"
        assert result[1] == "OPPOSE"

    def test_empty_input_returns_empty(self):
        mock_pipe = MagicMock()
        with patch.object(svc, "_get_pipeline", return_value=mock_pipe):
            result = svc.classify_stance_batch([], target_terms=[])
        assert result == []
