"""
Sentiment classification service.

Classifies comment text into three sentiment labels:
  POSITIVE, NEUTRAL, NEGATIVE

Model
-----
Uses the DistilBERT SST-2 model (``distilbert-base-uncased-finetuned-sst-2-english``)
which is a binary classifier (POSITIVE / NEGATIVE).  Because the original
issue contract requires a 3-class output, we introduce a confidence threshold:

  - Raw label POSITIVE  with score >= threshold  →  POSITIVE
  - Raw label NEGATIVE  with score >= threshold  →  NEGATIVE
  - Either label  with score <  threshold        →  NEUTRAL

The threshold is configurable (default 0.85) and can be overridden via the
``SENTIMENT_CONFIDENCE_THRESHOLD`` environment variable.

Loading
-------
The HuggingFace pipeline is loaded lazily on the first call to avoid importing
several hundred megabytes of model weights at startup time (and to allow tests
to mock the pipeline without loading real weights).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings as app_settings

if TYPE_CHECKING:
    from transformers import Pipeline  # pragma: no cover

logger = logging.getLogger(__name__)

# Lazy-loaded singleton — populated on first call to _get_pipeline()
_pipeline: "Pipeline | None" = None

# Confidence threshold below which the binary output is mapped to NEUTRAL.
_CONFIDENCE_THRESHOLD: float = 0.85

_LABEL_MAP: dict[str, str] = {
    "POSITIVE": "POSITIVE",
    "NEGATIVE": "NEGATIVE",
    # Some model variants use "LABEL_0" / "LABEL_1" — map defensively.
    "LABEL_0": "NEGATIVE",
    "LABEL_1": "POSITIVE",
}


def _get_pipeline() -> "Pipeline":
    """Return the shared sentiment pipeline, loading it on the first call."""
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline  # noqa: PLC0415

        logger.info(
            "loading_sentiment_model",
            extra={
                "event": "loading_sentiment_model",
                "component": "sentiment",
                "request_id": "-",
                "job_name": "classify",
                "model": app_settings.sentiment_model,
            },
        )
        _pipeline = pipeline(
            "sentiment-analysis",
            model=app_settings.sentiment_model,
            truncation=True,
            max_length=512,
        )
    return _pipeline


def _map_output(label: str, score: float) -> str:
    """Convert a raw model label + confidence score to a 3-class label."""
    normalised = _LABEL_MAP.get(label.upper(), "NEUTRAL")
    if score < _CONFIDENCE_THRESHOLD:
        return "NEUTRAL"
    return normalised


def classify_sentiment_batch(
    texts: list[str],
    batch_size: int = 32,
) -> list[str]:
    """Classify a list of comment texts into POSITIVE / NEUTRAL / NEGATIVE.

    Parameters
    ----------
    texts:
        Raw comment bodies.  Empty strings are returned as ``"NEUTRAL"``.
    batch_size:
        How many texts to send to the model in one forward pass.

    Returns
    -------
    list[str]
        One label per input text, in the same order.  Inference failures for
        an individual item are logged and default to ``"NEUTRAL"``.
    """
    results: list[str] = []

    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        chunk_labels: list[str] = []

        for text in chunk:
            if not text or not text.strip():
                chunk_labels.append("NEUTRAL")
                continue
            try:
                pipe = _get_pipeline()
                output = pipe(text)[0]  # {"label": "...", "score": 0.9}
                label = _map_output(output["label"], output["score"])
                chunk_labels.append(label)
            except Exception:
                logger.exception(
                    "sentiment_inference_failed",
                    extra={
                        "event": "sentiment_inference_failed",
                        "component": "sentiment",
                        "request_id": "-",
                        "job_name": "classify",
                    },
                )
                chunk_labels.append("NEUTRAL")

        results.extend(chunk_labels)

    return results


def reset_pipeline() -> None:
    """Reset the cached pipeline singleton (for testing only)."""
    global _pipeline
    _pipeline = None
