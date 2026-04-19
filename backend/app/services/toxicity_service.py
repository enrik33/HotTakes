"""
Toxicity scoring service.

Scores each comment body with a toxicity probability in [0.0, 1.0] using the
``toxigen/roberta-large-toxic-comments`` model (configured via
``settings.toxicity_model``).

Score semantics
---------------
0.0  — completely benign
1.0  — highly toxic

Bucket helpers
--------------
``toxicity_bucket()`` converts a numeric score into a human-readable tier for
frontend display:

  low     → score < 0.3
  medium  → 0.3 ≤ score < 0.7
  high    → score ≥ 0.7

Loading
-------
The pipeline is initialised lazily on the first call so unit tests can swap
in a mock without downloading multi-gigabyte model weights.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings as app_settings

if TYPE_CHECKING:
    from transformers import Pipeline  # pragma: no cover

logger = logging.getLogger(__name__)

_pipeline: "Pipeline | None" = None


def _get_pipeline() -> "Pipeline":
    """Return the shared toxicity pipeline, loading it on the first call."""
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline  # noqa: PLC0415

        logger.info(
            "loading_toxicity_model",
            extra={
                "event": "loading_toxicity_model",
                "component": "toxicity",
                "request_id": "-",
                "job_name": "classify",
                "model": app_settings.toxicity_model,
            },
        )
        _pipeline = pipeline(
            "text-classification",
            model=app_settings.toxicity_model,
            truncation=True,
            max_length=512,
        )
    return _pipeline


def _extract_score(output: dict) -> float:
    """Extract and clamp the toxicity probability from a model output dict.

    The roberta-large-toxic-comments model returns a dict with keys
    ``"label"`` and ``"score"``.  The label is "LABEL_1" (toxic) or
    "LABEL_0" (benign) and the score is the probability of *that* class.

    We always return the probability of being toxic:
      - If label == "LABEL_1" (toxic): score is already the toxic probability.
      - If label == "LABEL_0" (benign): the toxic probability is 1 - score.
    """
    label = (output.get("label") or "").upper()
    raw = float(output.get("score", 0.0))

    if label in ("TOXIC", "LABEL_1"):
        prob = raw
    else:
        # benign label — invert to get toxic probability
        prob = 1.0 - raw

    return max(0.0, min(1.0, prob))


def score_toxicity_batch(
    texts: list[str],
    batch_size: int = 32,
) -> list[float]:
    """Score a list of comment texts for toxicity.

    Parameters
    ----------
    texts:
        Raw comment bodies.  Empty/blank texts are scored 0.0 without
        calling the model.
    batch_size:
        Forward-pass chunk size.

    Returns
    -------
    list[float]
        Toxicity probability in [0.0, 1.0] for each input, in order.
        Per-item inference failures default to 0.0 (safe / benign).
    """
    results: list[float] = []

    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]

        for text in chunk:
            if not text or not text.strip():
                results.append(0.0)
                continue
            try:
                pipe = _get_pipeline()
                output = pipe(text)[0]
                results.append(_extract_score(output))
            except Exception:
                logger.exception(
                    "toxicity_inference_failed",
                    extra={
                        "event": "toxicity_inference_failed",
                        "component": "toxicity",
                        "request_id": "-",
                        "job_name": "classify",
                    },
                )
                results.append(0.0)

    return results


def toxicity_bucket(score: float) -> str:
    """Convert a numeric toxicity score into a display tier.

    Thresholds
    ----------
    low    → score < 0.3
    medium → 0.3 ≤ score < 0.7
    high   → score ≥ 0.7
    """
    if score >= 0.7:
        return "high"
    if score >= 0.3:
        return "medium"
    return "low"


def reset_pipeline() -> None:
    """Reset the cached pipeline singleton (for testing only)."""
    global _pipeline
    _pipeline = None
