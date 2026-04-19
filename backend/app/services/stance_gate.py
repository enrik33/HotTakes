"""
Target-aware stance gating.

Before running the stance classifier, this module checks whether a comment
body actually mentions the thread's subject.  Comments that do not reference
any of the thread's target terms are automatically labelled NEUTRAL (by rule),
skipping the more expensive ML inference step entirely.

Rules
-----
- If ``target_terms`` is empty the comment is considered on-target (no gating
  possible without a reference subject) and the caller should proceed to the
  stance model.
- Matching is case-insensitive and uses whole-word boundaries for single-word
  terms, substring matching for multi-word phrases (same strategy as
  keyword_filter.py).
"""

import re


def is_on_target(body: str, target_terms: list[str]) -> bool:
    """Return True if the comment body references at least one target term.

    Parameters
    ----------
    body:
        Raw comment text (may contain HTML entities from HN).
    target_terms:
        Extracted entity strings for the parent story, e.g.
        ``["GPT-4", "OpenAI"]``.  Comes from ``Post.target_terms`` split on
        commas.

    Returns
    -------
    bool
        ``True``  → comment is on-target; caller should run stance model.
        ``False`` → comment is off-target; caller should write NEUTRAL by rule.
    """
    # Normalise — strip whitespace and remove blank entries.
    cleaned = [t.strip() for t in target_terms if t.strip()]
    if not cleaned:
        # No usable target information — cannot gate, pass to model.
        return True

    body_lower = body.lower()

    for term in cleaned:
        term_lower = term.lower()
        if " " in term_lower:
            # Multi-word phrase: substring match is specific enough.
            if term_lower in body_lower:
                return True
        else:
            # Single word: require word boundary to avoid partial matches
            # (e.g. "ai" inside "raise" or "said").
            if re.search(r"\b" + re.escape(term_lower) + r"\b", body_lower):
                return True

    return False


def split_target_terms(raw: str | None) -> list[str]:
    """Parse the comma-separated ``Post.target_terms`` string into a list.

    Returns an empty list for ``None`` or blank values.
    """
    if not raw:
        return []
    return [t.strip() for t in raw.split(",") if t.strip()]
