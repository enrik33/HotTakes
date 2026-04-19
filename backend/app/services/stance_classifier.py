"""
Stance classifier service — v1 (4-class, zero-shot NLI).

Classifies a comment's stance relative to the thread's target subject into one
of four labels:

  SUPPORT  — commenter agrees with / endorses the target
  OPPOSE   — commenter disagrees with / criticises the target
  MIXED    — comment contains both supportive and critical elements
  NEUTRAL  — comment does not take a stance (off-topic / purely informational)

Approach
--------
We use a zero-shot cross-encoder NLI model
(``cross-encoder/nli-deberta-v3-small`` by default) via
``transformers.pipeline("zero-shot-classification")``.  The four candidate
labels are phrased as natural-language hypotheses that incorporate the primary
target entity so the model can reason about stance *relative to the subject*.

When ``target_terms`` is empty the generic hypothesis set is used so that the
classifier still produces one of the four valid labels.

Loading
-------
Lazy-loaded singleton — no model weights loaded until the first call.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.config import settings as app_settings

if TYPE_CHECKING:
    from transformers import Pipeline  # pragma: no cover

logger = logging.getLogger(__name__)

_pipeline: "Pipeline | None" = None

# Valid output labels in the order the model sees them.
_VALID_LABELS = {"SUPPORT", "OPPOSE", "MIXED", "NEUTRAL"}

# Hypothesis templates when a primary target entity is available.
_TARGETED_TEMPLATES = [
    "This comment supports {target}.",
    "This comment opposes {target}.",
    "This comment has a mixed opinion about {target}.",
    "This comment is unrelated to {target}.",
]

# Generic hypotheses when no target term exists.
_GENERIC_TEMPLATES = [
    "This comment supports the main subject.",
    "This comment opposes the main subject.",
    "This comment has a mixed opinion about the main subject.",
    "This comment is off-topic or neutral.",
]

# Map hypothesis index → canonical label.
_INDEX_TO_LABEL = ["SUPPORT", "OPPOSE", "MIXED", "NEUTRAL"]


def _get_pipeline() -> "Pipeline":
    """Return the shared zero-shot classification pipeline."""
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline  # noqa: PLC0415

        logger.info(
            "loading_stance_model",
            extra={
                "event": "loading_stance_model",
                "component": "stance",
                "request_id": "-",
                "job_name": "classify",
                "model": app_settings.stance_classifier_model,
            },
        )
        _pipeline = pipeline(
            "zero-shot-classification",
            model=app_settings.stance_classifier_model,
        )
    return _pipeline


def _build_candidate_labels(target_terms: list[str]) -> list[str]:
    """Build the four hypothesis strings for the NLI model."""
    primary = target_terms[0].strip() if target_terms else ""
    if primary:
        return [t.format(target=primary) for t in _TARGETED_TEMPLATES]
    return list(_GENERIC_TEMPLATES)


def _top_label(result: dict) -> str:
    """Extract the highest-scoring label and map it to a canonical stance."""
    # Zero-shot output: {"labels": [...], "scores": [...]}
    # Labels are sorted highest-score first.
    top_hypothesis: str = result["labels"][0]
    for idx, template in enumerate(_TARGETED_TEMPLATES + _GENERIC_TEMPLATES):
        # Match by checking whether the hypothesis *starts with* the template
        # prefix (target substitution may vary).
        for i, tmpl in enumerate(_TARGETED_TEMPLATES):
            verb = tmpl.split(" ")[2]  # "supports" / "opposes" / "has" / "is"
            if verb in top_hypothesis:
                return _INDEX_TO_LABEL[i]
    # Fallback — should not normally occur.
    return "NEUTRAL"


def classify_stance_batch(
    texts: list[str],
    target_terms: list[str],
    batch_size: int = 16,
) -> list[str]:
    """Classify each text's stance relative to ``target_terms``.

    Parameters
    ----------
    texts:
        Comment bodies to classify.  Empty/blank texts receive ``"NEUTRAL"``.
    target_terms:
        Entity terms extracted from the parent story (e.g. ``["GPT-4"]``).
        Pass an empty list when no target is available.
    batch_size:
        Items processed per NLI forward-pass chunk.

    Returns
    -------
    list[str]
        One of ``SUPPORT``, ``OPPOSE``, ``MIXED``, ``NEUTRAL`` per input,
        in the same order.  Per-item failures default to ``"NEUTRAL"``.
    """
    candidate_labels = _build_candidate_labels(target_terms)
    results: list[str] = []

    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]

        for text in chunk:
            if not text or not text.strip():
                results.append("NEUTRAL")
                continue
            try:
                pipe = _get_pipeline()
                output = pipe(text, candidate_labels=candidate_labels)
                results.append(_top_label(output))
            except Exception:
                logger.exception(
                    "stance_inference_failed",
                    extra={
                        "event": "stance_inference_failed",
                        "component": "stance",
                        "request_id": "-",
                        "job_name": "classify",
                    },
                )
                results.append("NEUTRAL")

    return results


def reset_pipeline() -> None:
    """Reset the cached pipeline singleton (for testing only)."""
    global _pipeline
    _pipeline = None
