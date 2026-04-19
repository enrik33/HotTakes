"""
Tests for the target-aware stance gating rule (Issue #17).
"""

from app.services.stance_gate import is_on_target, split_target_terms


# ---------------------------------------------------------------------------
# is_on_target — basic matching
# ---------------------------------------------------------------------------


class TestIsOnTarget:
    def test_empty_target_terms_passes_through(self):
        """No target terms → always on-target (no gating without a subject)."""
        assert is_on_target("This is a great idea.", []) is True

    def test_single_term_present(self):
        """Comment contains the target word → on-target."""
        assert is_on_target("I think GPT-4 is impressive.", ["GPT-4"]) is True

    def test_single_term_absent(self):
        """Comment does not mention the target → off-target."""
        assert is_on_target("The weather is nice today.", ["GPT-4"]) is False

    def test_case_insensitive_match(self):
        """Matching is case-insensitive."""
        assert is_on_target("openai released a new model.", ["OpenAI"]) is True
        assert is_on_target("OPENAI is great.", ["openai"]) is True

    def test_word_boundary_single_word(self):
        """Single-word terms must match on word boundaries."""
        # "ai" should NOT match inside "raise" or "said"
        assert is_on_target("She raised the price.", ["ai"]) is False
        # but should match standalone "AI"
        assert is_on_target("AI is changing the world.", ["ai"]) is True

    def test_multi_word_phrase_present(self):
        """Multi-word target terms use substring matching."""
        assert (
            is_on_target("Open source licensing is complex.", ["open source"]) is True
        )

    def test_multi_word_phrase_absent(self):
        assert is_on_target("Proprietary software dominates.", ["open source"]) is False

    def test_multiple_terms_any_match(self):
        """Any one of multiple target terms is sufficient."""
        assert is_on_target("Claude is my favorite model.", ["GPT-4", "Claude"]) is True

    def test_multiple_terms_none_match(self):
        """None of the target terms present → off-target."""
        assert (
            is_on_target("I love hiking in the mountains.", ["GPT-4", "Claude"])
            is False
        )

    def test_empty_body_with_terms(self):
        """Empty comment body → off-target."""
        assert is_on_target("", ["OpenAI"]) is False

    def test_term_partial_in_larger_word_no_match(self):
        """Single word 'rust' should not match 'rustle' or 'trustworthy'."""
        assert is_on_target("The leaves rustled in the wind.", ["rust"]) is False
        assert is_on_target("Rust is a systems language.", ["rust"]) is True

    def test_blank_terms_in_list_are_ignored(self):
        """Empty strings in the terms list are skipped."""
        assert is_on_target("Some comment.", ["", "  ", "GPT-4"]) is False
        assert is_on_target("Talking about GPT-4 here.", ["", "  ", "GPT-4"]) is True

    def test_list_with_only_blanks_passes_through(self):
        """A list containing only empty strings behaves like empty list."""
        # All terms stripped to empty → passes through (treated as no target)
        assert is_on_target("Some unrelated comment.", ["", "  "]) is True


# ---------------------------------------------------------------------------
# split_target_terms
# ---------------------------------------------------------------------------


class TestSplitTargetTerms:
    def test_none_returns_empty(self):
        assert split_target_terms(None) == []

    def test_empty_string_returns_empty(self):
        assert split_target_terms("") == []

    def test_single_term(self):
        assert split_target_terms("OpenAI") == ["OpenAI"]

    def test_multiple_terms(self):
        assert split_target_terms("GPT-4,Claude,Gemini") == [
            "GPT-4",
            "Claude",
            "Gemini",
        ]

    def test_whitespace_trimmed(self):
        assert split_target_terms("  GPT-4 , Claude , Gemini  ") == [
            "GPT-4",
            "Claude",
            "Gemini",
        ]

    def test_trailing_comma_ignored(self):
        assert split_target_terms("GPT-4,Claude,") == ["GPT-4", "Claude"]

    def test_blank_segments_ignored(self):
        assert split_target_terms(",,,GPT-4,,,") == ["GPT-4"]
