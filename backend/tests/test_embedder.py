"""
Tests for the embedding generation service (Issue #24).

All tests mock the SentenceTransformer model — no weights required.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

import app.services.embedder as svc
from app.services.embedder import (
    _EMBEDDING_DIM,
    _ZERO_VECTOR,
    generate_comment_embeddings,
    generate_embeddings_batch,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singleton():
    svc.reset_pipeline()
    yield
    svc.reset_pipeline()


def _fake_encode(text, convert_to_numpy=True):
    """Return a mock numpy-like array (list works because we call .tolist())."""
    mock = MagicMock()
    mock.tolist.return_value = [0.1] * _EMBEDDING_DIM
    return mock


def _make_db(comments=None):
    """Return a mock Session whose execute chain yields *comments*."""
    scalars = MagicMock()
    scalars.unique.return_value = iter(comments or [])
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars
    db = MagicMock()
    db.execute.return_value = execute_result
    return db


def _make_comment(id: int, body: str = "Some text about AI"):
    c = MagicMock()
    c.id = id
    c.body = body
    return c


# ---------------------------------------------------------------------------
# generate_embeddings_batch
# ---------------------------------------------------------------------------


class TestGenerateEmbeddingsBatch:
    def test_single_text_returns_vector(self):
        mock_model = MagicMock()
        mock_model.encode.side_effect = _fake_encode
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch(["hello world"])
        assert len(result) == 1
        assert len(result[0]) == _EMBEDDING_DIM

    def test_empty_string_returns_zero_vector_without_model(self):
        mock_model = MagicMock()
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch([""])
        mock_model.encode.assert_not_called()
        assert result == [list(_ZERO_VECTOR)]

    def test_whitespace_only_returns_zero_vector(self):
        mock_model = MagicMock()
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch(["   \t\n"])
        mock_model.encode.assert_not_called()
        assert result == [list(_ZERO_VECTOR)]

    def test_order_preserved(self):
        calls = []

        def encode_side(text, convert_to_numpy=True):
            calls.append(text)
            mock = MagicMock()
            mock.tolist.return_value = [float(len(calls))] * _EMBEDDING_DIM
            return mock

        mock_model = MagicMock()
        mock_model.encode.side_effect = encode_side
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch(["a", "bb", "ccc"])

        assert result[0][0] == 1.0
        assert result[1][0] == 2.0
        assert result[2][0] == 3.0

    def test_batch_chunking(self):
        mock_model = MagicMock()
        mock_model.encode.side_effect = _fake_encode
        texts = ["text"] * 5
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch(texts, batch_size=2)
        assert len(result) == 5
        assert mock_model.encode.call_count == 5

    def test_encode_error_returns_zero_vector(self):
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("CUDA OOM")
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch(["some text"])
        assert result == [list(_ZERO_VECTOR)]

    def test_error_on_one_item_does_not_abort_batch(self):
        def encode_side(text, convert_to_numpy=True):
            if text == "bad":
                raise RuntimeError("encode fail")
            mock = MagicMock()
            mock.tolist.return_value = [0.5] * _EMBEDDING_DIM
            return mock

        mock_model = MagicMock()
        mock_model.encode.side_effect = encode_side
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch(["good", "bad", "good"])
        assert result[0][0] == 0.5
        assert result[1] == list(_ZERO_VECTOR)
        assert result[2][0] == 0.5

    def test_empty_input_returns_empty(self):
        mock_model = MagicMock()
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_embeddings_batch([])
        assert result == []


# ---------------------------------------------------------------------------
# generate_comment_embeddings
# ---------------------------------------------------------------------------


class TestGenerateCommentEmbeddings:
    def test_returns_zeros_when_no_pending_comments(self):
        db = _make_db([])
        result = generate_comment_embeddings(db)
        assert result == {"embedded": 0, "errors": 0}

    def test_commit_not_called_when_nothing_to_embed(self):
        db = _make_db([])
        generate_comment_embeddings(db)
        db.commit.assert_not_called()

    def test_writes_embedding_row_for_each_comment(self):
        comment = _make_comment(1, body="AI is taking over")
        added = []
        db = _make_db([comment])
        db.add.side_effect = added.append

        mock_model = MagicMock()
        mock_model.encode.side_effect = _fake_encode
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_comment_embeddings(db)

        assert result["embedded"] == 1
        assert result["errors"] == 0
        assert len(added) == 1
        emb = added[0]
        assert emb.comment_id == 1
        stored_vector = json.loads(emb.embedding_vector)
        assert len(stored_vector) == _EMBEDDING_DIM

    def test_commit_called_after_writes(self):
        comment = _make_comment(1)
        db = _make_db([comment])
        mock_model = MagicMock()
        mock_model.encode.side_effect = _fake_encode
        with patch.object(svc, "_get_model", return_value=mock_model):
            generate_comment_embeddings(db)
        db.commit.assert_called_once()

    def test_encode_error_counts_as_error_and_skips_write(self):
        comment = _make_comment(1, body="Some text")
        added = []
        db = _make_db([comment])
        db.add.side_effect = added.append

        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("boom")
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_comment_embeddings(db)

        assert result["errors"] == 1
        assert result["embedded"] == 0
        assert len(added) == 0

    def test_multiple_comments_embedded_correctly(self):
        comments = [_make_comment(i) for i in range(1, 4)]
        added = []
        db = _make_db(comments)
        db.add.side_effect = added.append

        mock_model = MagicMock()
        mock_model.encode.side_effect = _fake_encode
        with patch.object(svc, "_get_model", return_value=mock_model):
            result = generate_comment_embeddings(db)

        assert result["embedded"] == 3
        assert result["errors"] == 0
        assert len(added) == 3
