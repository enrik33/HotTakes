"""Tests for the _pick_representative helper (Issue #27)."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from app.services.clusterer import _pick_representative


def _make_comment(comment_id: int, body: str) -> MagicMock:
    c = MagicMock()
    c.id = comment_id
    c.body = body
    return c


def _vec(values: list[float]) -> np.ndarray:
    return np.array(values, dtype=np.float32)


class TestPickRepresentative:
    def test_single_long_comment_is_picked(self):
        body = "x" * 50  # >= min_quote_length (40)
        comment = _make_comment(1, body)
        centroid = _vec([1.0, 0.0])
        matrix = np.array([[1.0, 0.0]], dtype=np.float32)
        result = _pick_representative([comment], centroid, matrix)
        assert result == 1

    def test_short_comment_below_min_length_is_excluded(self):
        comment = _make_comment(1, "short")  # < 40 chars
        centroid = _vec([1.0, 0.0])
        matrix = np.array([[1.0, 0.0]], dtype=np.float32)
        result = _pick_representative([comment], centroid, matrix)
        assert result is None

    def test_returns_none_when_all_comments_too_short(self):
        comments = [_make_comment(i, "hi") for i in range(1, 4)]
        centroid = _vec([1.0, 0.0, 0.0])
        matrix = np.eye(3, dtype=np.float32)
        result = _pick_representative(comments, centroid, matrix)
        assert result is None

    def test_picks_comment_with_highest_cosine_similarity(self):
        # comment 1 → vec [1,0] → sim=1.0 with centroid [1,0]
        # comment 2 → vec [0,1] → sim=0.0 with centroid [1,0]
        body_long = "a" * 50
        c1 = _make_comment(1, body_long)
        c2 = _make_comment(2, body_long)
        centroid = _vec([1.0, 0.0])
        matrix = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        result = _pick_representative([c1, c2], centroid, matrix)
        assert result == 1

    def test_cosine_ranking_picks_closest(self):
        body_long = "b" * 50
        c1 = _make_comment(10, body_long)
        c2 = _make_comment(20, body_long)
        c3 = _make_comment(30, body_long)
        centroid = _vec([0.0, 1.0])
        # c2 has [0,1] → sim=1.0; best
        matrix = np.array([[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]], dtype=np.float32)
        result = _pick_representative([c1, c2, c3], centroid, matrix)
        assert result == 20

    def test_min_length_gate_excludes_short_among_many(self):
        long_body = "a" * 50
        short_body = "x" * 10
        # c1 is short (excluded), c2 is long → c2 picked
        c1 = _make_comment(1, short_body)
        c2 = _make_comment(2, long_body)
        centroid = _vec([1.0, 0.0])
        # c1 has higher cosine sim but body too short
        matrix = np.array([[1.0, 0.0], [0.5, 0.5]], dtype=np.float32)
        result = _pick_representative([c1, c2], centroid, matrix)
        assert result == 2

    def test_zero_centroid_returns_none(self):
        c = _make_comment(1, "a" * 50)
        centroid = _vec([0.0, 0.0])
        matrix = np.array([[1.0, 0.0]], dtype=np.float32)
        result = _pick_representative([c], centroid, matrix)
        assert result is None

    def test_zero_embedding_vector_skipped(self):
        c1 = _make_comment(1, "a" * 50)  # zero vec → skip
        c2 = _make_comment(2, "b" * 50)
        centroid = _vec([1.0, 0.0])
        matrix = np.array([[0.0, 0.0], [1.0, 0.0]], dtype=np.float32)
        result = _pick_representative([c1, c2], centroid, matrix)
        assert result == 2

    def test_empty_comment_list_returns_none(self):
        centroid = _vec([1.0, 0.0])
        matrix = np.empty((0, 2), dtype=np.float32)
        result = _pick_representative([], centroid, matrix)
        assert result is None

    def test_exact_min_length_comment_included(self):
        from app.config import settings

        body = "y" * settings.min_quote_length  # exactly 40 chars
        c = _make_comment(42, body)
        centroid = _vec([1.0, 0.0])
        matrix = np.array([[1.0, 0.0]], dtype=np.float32)
        result = _pick_representative([c], centroid, matrix)
        assert result == 42

    def test_one_short_one_exact_length(self):
        from app.config import settings

        c1 = _make_comment(1, "x" * (settings.min_quote_length - 1))  # too short
        c2 = _make_comment(2, "y" * settings.min_quote_length)  # exactly ok
        centroid = _vec([1.0, 0.0])
        matrix = np.array([[1.0, 0.0], [0.8, 0.0]], dtype=np.float32)
        result = _pick_representative([c1, c2], centroid, matrix)
        assert result == 2
