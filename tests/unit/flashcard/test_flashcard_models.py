import pytest
from uuid import uuid4


@pytest.mark.unit
class TestFlashcardDeckModel:

    def test_deck_creation(self):
        from flashcard.models import Quiz
        deck = Quiz(title="Biology", subject_tag="Biology", difficulty_level="easy")
        assert deck.title == "Biology"
        assert deck.subject_tag == "Biology"

    def test_deck_id_default_configured(self):
        from flashcard.models import Quiz
        col = Quiz.__table__.c.quiz_id
        assert col.default is not None

    def test_two_decks_have_different_ids(self):
        from flashcard.models import Quiz
        d1 = Quiz(title="A")
        d2 = Quiz(title="B")
        d1.quiz_id = str(uuid4())
        d2.quiz_id = str(uuid4())
        assert d1.quiz_id != d2.quiz_id

    def test_deck_is_active_default_configured(self):
        from flashcard.models import Quiz
        col = Quiz.__table__.c.is_active
        assert col.default.arg is True

    def test_deck_optional_fields_default_none(self):
        from flashcard.models import Quiz
        deck = Quiz(title="Minimal")
        assert deck.description is None
        assert deck.subject_tag is None
        assert deck.estimated_time is None

    def test_deck_with_all_fields(self):
        from flashcard.models import Quiz
        deck = Quiz(
            title="Biology",
            description="Cell biology terms",
            subject_tag="Biology",
            difficulty_level="intermediate",
            estimated_time=20,
        )
        assert deck.description == "Cell biology terms"
        assert deck.estimated_time == 20


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

    def test_card_id_default_configured(self):
        from flashcard.models import QuizQuestion
        col = QuizQuestion.__table__.c.question_id
        assert col.default is not None

    def test_two_cards_have_different_ids(self):
        from flashcard.models import QuizQuestion
        qid = str(uuid4())
        c1 = QuizQuestion(quiz_id=qid, question_text="T1", correct_answer="D1", incorrect_answers=[])
        c2 = QuizQuestion(quiz_id=qid, question_text="T2", correct_answer="D2", incorrect_answers=[])
        c1.question_id = str(uuid4())
        c2.question_id = str(uuid4())
        assert c1.question_id != c2.question_id

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

    def test_card_difficulty_optional(self):
        from flashcard.models import QuizQuestion
        card = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="Term?",
            correct_answer="Def",
            incorrect_answers=[],
        )
        assert card.difficulty is None


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

    def test_card_reviewed_default_configured(self):
        from flashcard.models import FlashcardAnalytics
        col = FlashcardAnalytics.__table__.c.card_reviewed
        assert col.default.arg is True

    def test_card_reviewed_can_be_false(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(
            deck_id=str(uuid4()),
            user_id="u1",
            time_taken=1.0,
            card_reviewed=False,
        )
        assert a.card_reviewed is False

    def test_time_taken_is_float(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(deck_id=str(uuid4()), user_id="u1", time_taken=2.75)
        assert isinstance(a.time_taken, float)

    def test_analytics_stores_correct_deck_id(self):
        from flashcard.models import FlashcardAnalytics
        deck_id = str(uuid4())
        a = FlashcardAnalytics(deck_id=deck_id, user_id="u1", time_taken=3.0)
        assert a.deck_id == deck_id

    def test_analytics_stores_correct_user_id(self):
        from flashcard.models import FlashcardAnalytics
        a = FlashcardAnalytics(deck_id=str(uuid4()), user_id="user-xyz", time_taken=2.0)
        assert a.user_id == "user-xyz"
