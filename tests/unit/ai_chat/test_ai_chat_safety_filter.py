"""
tests/unit/ai_chat/test_ai_chat_safety_filter.py
"""
import pytest
from ai_chat.app.utils.moderation import contains_harmful_content


class TestContainsHarmfulContent:

    # ── Clean inputs ────────────────────────────────────────────────────────

    def test_clean_text_returns_false(self):
        assert contains_harmful_content("What is photosynthesis?") is False

    def test_empty_string_returns_false(self):
        assert contains_harmful_content("") is False

    def test_normal_question_returns_false(self):
        assert contains_harmful_content("How do I bake a chocolate cake?") is False

    def test_technical_query_returns_false(self):
        assert contains_harmful_content("Explain gradient descent in neural networks") is False

    # ── Harmful word detection ──────────────────────────────────────────────

    def test_exact_harmful_word_returns_true(self):
        assert contains_harmful_content("I want to kill someone") is True

    def test_hate_word_returns_true(self):
        assert contains_harmful_content("I hate everything") is True

    def test_terror_word_returns_true(self):
        assert contains_harmful_content("terror attack plan") is True

    def test_suicide_word_returns_true(self):
        assert contains_harmful_content("suicide methods") is True

    def test_bomb_word_returns_true(self):
        assert contains_harmful_content("how to build a bomb") is True

    def test_gun_word_returns_true(self):
        assert contains_harmful_content("where to buy a gun illegally") is True

    # ── Case insensitivity ──────────────────────────────────────────────────

    def test_uppercase_harmful_word_detected(self):
        assert contains_harmful_content("KILL all processes") is True

    def test_mixed_case_harmful_word_detected(self):
        assert contains_harmful_content("This is HaTe speech") is True

    def test_clean_text_uppercase_returns_false(self):
        assert contains_harmful_content("WHAT IS THE CAPITAL OF FRANCE?") is False

    # ── Substring matching behaviour ────────────────────────────────────────

    def test_harmful_word_embedded_in_sentence(self):
        # "murder" appears mid-sentence — must still be caught
        assert contains_harmful_content("The murder mystery novel was gripping") is True

    def test_word_that_contains_harmful_substring(self):
        # "drugs" is in HARMFUL_WORDS; "drugstore" contains it as substring
        # This is expected behaviour for the current implementation
        assert contains_harmful_content("I need to go to the drugstore") is True

    # ── Multiple harmful words ──────────────────────────────────────────────

    def test_multiple_harmful_words_returns_true(self):
        assert contains_harmful_content("violence and hate and murder") is True

    def test_one_harmful_word_among_clean_text_returns_true(self):
        assert contains_harmful_content("This is a great day but I hate Mondays") is True