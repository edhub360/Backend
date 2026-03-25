import pytest
from uuid import uuid4


@pytest.mark.unit
class TestFlashcardDeckModel:

    def test_deck_creation(self):
        from flashcard.models import Quiz
        deck = Quiz(title="Biology", subject_tag="Biology", difficulty_level="easy")
        assert deck.title == "Biology"
        assert deck.subject_tag == "Biology"

    def test_deck_id_auto_generated(self):
        from flashcard.models import Quiz
        deck = Quiz(title="Test")
        assert deck.quiz_id is not None
        assert len(deck.quiz_id) == 36

    def test_two_decks_have_different_ids(self):
        from flashcard.models import Quiz
        assert Quiz(title="A").quiz_id != Quiz(title="B").quiz_id

    def test_deck_is_active_defaults_true(self):
        from flashcard.models import Quiz
        assert Quiz(title="Test").is_active is True

    def test_deck_optional_fields_default_none(self):
        from flashcard.models import Quiz
        deck = Quiz(title="Minimal")
        assert deck.description is None
        assert deck.subject_tag is None
        assert deck.estimated_time is None


@pytest.mark.unit
class TestFlashcardCardModel:

    def test_card_creation(self):
        from flashcard.models import QuizQuestion
        card = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="What is mitosis?",
            correct_answer="Cell division",
            incorrect_answers=[],
        )
        assert card.question_text == "What is mitosis?"
        assert card.correct_answer == "Cell division"

    def test_card_id_auto_generated(self):
        from flashcard.models import QuizQuestion
        card = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="Term?",
            correct_answer="Definition",
            incorrect_answers=[],
        )
        assert card.question_id is not None
        assert len(card.question_id) == 36

    def test_card_hint_defaults_none(self):
        from flashcard.models import QuizQuestion
        card = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="Term?",
            correct_answer="Def",
            incorrect_answers=[],
        )
        assert card.explanation is None

    def test_card_with_hint(self):
        from flashcard.models import QuizQuestion
        card = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="What is DNA?",
            correct_answer="Deoxyribonucleic acid",
            incorrect_answers=[],
            explanation="Found in nucleus",
        )
        assert card.explanation == "Found in nucleus"


@pytest.mark.unit
class TestFlashcardAnalyticsModel:

    def test_analytics_creation(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(
            deck_id=str(uuid4()),
            user_id="user-123",
            card_reviewed=True,
            time_taken=5.5,
        )
        assert a.user_id == "user-123"
        assert a.time_taken == 5.5

    def test_card_reviewed_defaults_true(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(deck_id=str(uuid4()), user_id="u1", time_taken=2.0)
        assert a.card_reviewed is True

    def test_time_taken_is_float(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(deck_id=str(uuid4()), user_id="u1", time_taken=2.75)
        assert isinstance(a.time_taken, float)
