"""
Keyword extraction service (Issue #26).

Extracts representative keywords from a list of comment texts using TF-IDF.
When fewer than 3 texts are available, falls back to simple term frequency.
"""

from __future__ import annotations

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

# Common English stop-words (augments scikit-learn's built-in list for
# domain-specific noise without importing NLTK).
_EXTRA_STOP: set[str] = {
    "like",
    "just",
    "think",
    "know",
    "really",
    "also",
    "even",
    "make",
    "way",
    "lot",
    "things",
    "thing",
    "people",
    "would",
    "could",
    "something",
    "much",
    "many",
    "very",
    "good",
    "great",
    "get",
    "got",
    "going",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    return re.findall(r"[a-z]{2,}", text.lower())


def extract_keywords(texts: list[str], n_keywords: int = 8) -> list[str]:
    """Return up to *n_keywords* representative keywords for a group of texts.

    Parameters
    ----------
    texts:
        Raw comment bodies for a single cluster.
    n_keywords:
        Maximum number of keywords to return.

    Returns
    -------
    list[str]
        Keywords ordered by relevance, empty list when *texts* is empty.
    """
    if not texts:
        return []

    if len(texts) < 3:
        return _term_frequency_fallback(texts, n_keywords)

    return _tfidf_keywords(texts, n_keywords)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _tfidf_keywords(texts: list[str], n_keywords: int) -> list[str]:
    """TF-IDF based extraction using scikit-learn (deferred import)."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: PLC0415

        vec = TfidfVectorizer(
            max_features=500,
            stop_words="english",
            ngram_range=(1, 2),
        )
        tfidf_matrix = vec.fit_transform(texts)
        feature_names: list[str] = vec.get_feature_names_out().tolist()

        # Mean TF-IDF score across documents
        import numpy as np  # noqa: PLC0415

        mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
        top_indices = mean_scores.argsort()[::-1]

        keywords: list[str] = []
        for idx in top_indices:
            term = feature_names[idx]
            # Skip if any token is an extra stop-word
            if any(tok in _EXTRA_STOP for tok in term.split()):
                continue
            keywords.append(term)
            if len(keywords) >= n_keywords:
                break
        return keywords
    except Exception:
        logger.exception("tfidf_extraction_failed")
        return _term_frequency_fallback(texts, n_keywords)


def _term_frequency_fallback(texts: list[str], n_keywords: int) -> list[str]:
    """Simple term-frequency fallback for small clusters (< 3 docs)."""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS  # noqa: PLC0415

    stop = set(ENGLISH_STOP_WORDS) | _EXTRA_STOP
    counter: Counter = Counter()
    for text in texts:
        for token in _tokenize(text):
            if token not in stop:
                counter[token] += 1
    return [word for word, _ in counter.most_common(n_keywords)]
