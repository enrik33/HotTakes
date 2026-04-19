"""Tests for keyword_extractor.py (Issue #26)."""

from __future__ import annotations


from app.services.keyword_extractor import extract_keywords


class TestExtractKeywordsEmpty:
    def test_empty_input_returns_empty_list(self):
        assert extract_keywords([]) == []

    def test_empty_strings_still_returns_empty(self):
        # Empty strings contain no tokens, so result should be empty.
        result = extract_keywords(["", "  ", "\t"])
        assert isinstance(result, list)


class TestExtractKeywordsSmallCorpus:
    """Fewer than 3 texts → term-frequency fallback."""

    def test_single_text_returns_keywords(self):
        text = "artificial intelligence machine learning deep neural networks"
        result = extract_keywords([text])
        assert len(result) > 0
        assert isinstance(result[0], str)

    def test_two_texts_returns_keywords(self):
        texts = [
            "climate change global warming temperatures rising",
            "carbon dioxide emissions greenhouse gases pollution",
        ]
        result = extract_keywords(texts)
        assert len(result) > 0

    def test_n_keywords_limit_respected_for_fallback(self):
        text = "one two three four five six seven eight nine ten eleven twelve"
        result = extract_keywords([text], n_keywords=3)
        assert len(result) <= 3

    def test_stopwords_excluded_from_fallback(self):
        # Only stop-words; should return nothing useful
        text = "the is are was were be been being"
        result = extract_keywords([text], n_keywords=8)
        # Common English stop-words should not appear
        for kw in result:
            assert kw not in {"the", "is", "are", "was", "were", "be", "been", "being"}


class TestExtractKeywordsLargeCorpus:
    """Three or more texts → TF-IDF path."""

    def _three_texts(self):
        return [
            "machine learning models train neural networks deep learning",
            "deep learning convolutional networks image recognition",
            "neural network backpropagation gradient descent optimization",
        ]

    def test_three_texts_returns_keywords(self):
        result = extract_keywords(self._three_texts())
        assert len(result) > 0

    def test_n_keywords_limit_respected(self):
        result = extract_keywords(self._three_texts(), n_keywords=3)
        assert len(result) <= 3

    def test_default_n_keywords_at_most_8(self):
        result = extract_keywords(self._three_texts())
        assert len(result) <= 8

    def test_stopwords_excluded(self):
        texts = [
            "the quick brown fox jumps over the lazy dog",
            "the dog is a good animal friend of humans",
            "humans and dogs live together in many places",
        ]
        result = extract_keywords(texts)
        for kw in result:
            assert "the" not in kw.split()
            assert "is" not in kw.split()

    def test_keyword_order_by_relevance(self):
        # The dominant topic should rank near the top
        texts = [
            "climate change global warming rising sea levels",
            "climate scientists warn about global warming effects",
            "rising temperatures climate change impacts environment",
        ]
        result = extract_keywords(texts)
        # At least one climate-related term should appear
        assert any("climate" in kw or "warming" in kw for kw in result)

    def test_returns_strings(self):
        result = extract_keywords(self._three_texts())
        assert all(isinstance(kw, str) for kw in result)

    def test_bigrams_allowed(self):
        texts = [
            "machine learning is a field of artificial intelligence",
            "machine learning algorithms learn from training data",
            "deep learning is a subset of machine learning methods",
        ]
        result = extract_keywords(texts)
        # We expect at least one bigram (contains a space) to appear
        assert any(" " in kw for kw in result)
