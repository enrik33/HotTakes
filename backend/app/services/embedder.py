"""
Embedding generation service.

Generates 384-dimensional semantic vectors for comment bodies using
``sentence-transformers/all-MiniLM-L6-v2`` (configured via
``settings.embedding_model``).

The embeddings are stored as JSON-serialised float lists in the
``Embedding.embedding_vector`` column so they can be retrieved for clustering
without a pgvector extension.

Loading
-------
The SentenceTransformer model is lazy-loaded on the first call — unit tests
can patch ``_get_model`` to avoid downloading multi-GB weights.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.config import settings as app_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer as _STType  # pragma: no cover

logger = logging.getLogger(__name__)

_EMBEDDING_DIM: int = 384  # all-MiniLM-L6-v2 output dimension
_ZERO_VECTOR: list[float] = [0.0] * _EMBEDDING_DIM

_model: "_STType | None" = None


def _get_model() -> "_STType":
    """Return the shared SentenceTransformer, loading it on the first call."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        logger.info(
            "loading_embedding_model",
            extra={
                "event": "loading_embedding_model",
                "component": "embedder",
                "request_id": "-",
                "job_name": "cluster",
                "model": app_settings.embedding_model,
            },
        )
        _model = SentenceTransformer(app_settings.embedding_model)
    return _model


def generate_embeddings_batch(
    texts: list[str],
    batch_size: int = 64,
) -> list[list[float]]:
    """Return a semantic embedding vector for each text.

    Parameters
    ----------
    texts:
        Raw comment bodies.  Empty or whitespace-only texts receive a zero
        vector without going through the model.
    batch_size:
        Number of texts encoded per forward pass.

    Returns
    -------
    list[list[float]]
        One 384-dim float list per input, in the same order.  Per-item
        encoding failures return the zero vector.
    """
    results: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        for text in chunk:
            if not text or not text.strip():
                results.append(list(_ZERO_VECTOR))
                continue
            try:
                model = _get_model()
                raw = model.encode(text, convert_to_numpy=True).tolist()
                # Round to 6 dp so the JSON fits in the varchar column
                vector = [round(v, 6) for v in raw]
                results.append(vector)
            except Exception:
                logger.exception(
                    "embedding_inference_failed",
                    extra={
                        "event": "embedding_inference_failed",
                        "component": "embedder",
                        "request_id": "-",
                        "job_name": "cluster",
                    },
                )
                results.append(list(_ZERO_VECTOR))

    return results


def generate_comment_embeddings(db, batch_size: int = 64) -> dict:
    """Generate and persist embeddings for all un-embedded comments.

    Queries ``Comment LEFT JOIN Embedding WHERE Embedding.id IS NULL`` to find
    comments that still need embedding, encodes them in batches, and writes
    ``Embedding`` rows to the database.

    Parameters
    ----------
    db:
        SQLAlchemy ``Session``.
    batch_size:
        Encoding batch size passed to :func:`generate_embeddings_batch`.

    Returns
    -------
    dict
        ``{"embedded": int, "errors": int}``
    """
    from sqlalchemy import select  # noqa: PLC0415

    from app.models import Comment, Embedding  # noqa: PLC0415

    stmt = (
        select(Comment)
        .outerjoin(Embedding, Embedding.comment_id == Comment.id)
        .where(Embedding.id.is_(None))
        .where(Comment.body.isnot(None))
        .where(Comment.body != "")
        .order_by(Comment.id.asc())
    )
    comments: list[Comment] = list(db.execute(stmt).scalars().unique())

    if not comments:
        logger.info(
            "embed_no_pending",
            extra={
                "event": "embed_no_pending",
                "component": "embedder",
                "request_id": "-",
                "job_name": "cluster",
            },
        )
        return {"embedded": 0, "errors": 0}

    texts = [c.body for c in comments]
    vectors = generate_embeddings_batch(texts, batch_size=batch_size)

    embedded = 0
    errors = 0
    for comment, vector in zip(comments, vectors):
        if vector == _ZERO_VECTOR:
            # Zero vectors come from blank texts or encoding errors — skip
            # persisting a noise embedding.  Blank bodies are filtered above,
            # so a zero here means an inference error occurred.
            errors += 1
            continue
        try:
            db.add(
                Embedding(
                    comment_id=comment.id,
                    embedding_vector=json.dumps(vector),
                    computed_at=datetime.now(timezone.utc),
                )
            )
            embedded += 1
        except Exception:
            logger.exception(
                "embed_write_failed",
                extra={
                    "event": "embed_write_failed",
                    "component": "embedder",
                    "request_id": "-",
                    "job_name": "cluster",
                    "comment_id": comment.id,
                },
            )
            errors += 1

    db.commit()

    logger.info(
        "embed_job_done",
        extra={
            "event": "embed_job_done",
            "component": "embedder",
            "request_id": "-",
            "job_name": "cluster",
            "embedded": embedded,
            "errors": errors,
        },
    )
    return {"embedded": embedded, "errors": errors}


def reset_pipeline() -> None:
    """Reset the cached model singleton (for testing only)."""
    global _model
    _model = None
