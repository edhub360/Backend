import pytest
from uuid import uuid4
from datetime import datetime
import pydantic


@pytest.mark.unit
class TestFlashcardItemSchema:

    def test_valid_card(self):
        from flashcard.schemas import FlashcardItem
        card = FlashcardItem(card_id=str(uuid4()), front_text="Term", back_text="Definition")
        assert card.front_text == "Term"
        assert card.hint is None

    def test_card_with_hint(self):
        from flashcard.schemas import FlashcardItem
        card = FlashcardItem(
            card_id=str(uuid4()),
            front_text="Term",
            back_text="Definition",
            hint="A clue",
        )
        assert card.hint == "A clue"

    def test_missing_back_text_raises(self):
        from flashcard.schemas import FlashcardItem
        with pytest.raises(pydantic.ValidationError):
            FlashcardItem(card_id=str(uuid4()), front_text="Term only")


@pytest.mark.unit
class TestFlashcardDeckSchemas:

    def test_deck_list_item_valid(self):
        from flashcard.schemas import FlashcardDeckListItem
        deck = FlashcardDeckListItem(
            deck_id=str(uuid4()), title="Biology",
            description="Cell bio", subject_tag="Biology",
            difficulty_level="easy", total_cards=20, is_active=True,
        )
        assert deck.total_cards == 20

    def test_deck_detail_empty_cards_default(self):
        from flashcard.schemas import FlashcardDeckDetail
        deck = FlashcardDeckDetail(
            deck_id=str(uuid4()), title="Empty",
            description="None", subject_tag="General", difficulty_level="easy",
        )
        assert deck.cards == []

    def test_deck_detail_with_multiple_cards(self):
        from flashcard.schemas import FlashcardDeckDetail, FlashcardItem
        cards = [
            FlashcardItem(card_id=str(uuid4()), front_text=f"T{i}", back_text=f"D{i}")
            for i in range(3)
        ]
        deck = FlashcardDeckDetail(
            deck_id=str(uuid4()), title="Full",
            description="Has cards", subject_tag="Science", difficulty_level="hard",
            cards=cards,
        )
        assert len(deck.cards) == 3


@pytest.mark.unit
class TestFlashcardAnalyticsSchemas:

    def test_analytics_create_valid(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        payload = FlashcardAnalyticsCreate(
            deck_id=str(uuid4()), user_id="user-123",
            card_reviewed=True, time_taken=4.5,
        )
        assert payload.time_taken == 4.5

    def test_card_reviewed_defaults_true(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        payload = FlashcardAnalyticsCreate(
            deck_id=str(uuid4()), user_id="user-123", time_taken=3.0,
        )
        assert payload.card_reviewed is True

    def test_missing_time_taken_raises(self):
        from flashcard.schemas import FlashcardAnalyticsCreate
        with pytest.raises(pydantic.ValidationError):
            FlashcardAnalyticsCreate(deck_id=str(uuid4()), user_id="user-123")

    def test_analytics_out_has_reviewed_at(self):
        from flashcard.schemas import FlashcardAnalyticsOut
        out = FlashcardAnalyticsOut(
            analytics_id=str(uuid4()), deck_id=str(uuid4()),
            user_id="user-123", card_reviewed=True,
            time_taken=2.5, reviewed_at=datetime.utcnow(),
        )
        assert isinstance(out.reviewed_at, datetime)


@pytest.mark.unit
class TestPaginationMetaSchema:

    def test_has_more_true(self):
        from flashcard.schemas import PaginationMeta
        meta = PaginationMeta(total=50, offset=0, limit=6, has_more=True)
        assert meta.has_more is True

    def test_has_more_false(self):
        from flashcard.schemas import PaginationMeta
        meta = PaginationMeta(total=6, offset=0, limit=6, has_more=False)
        assert meta.has_more is False

    def test_all_fields_correct(self):
        from flashcard.schemas import PaginationMeta
        meta = PaginationMeta(total=100, offset=12, limit=6, has_more=True)
        assert meta.total == 100
        assert meta.offset == 12
        assert meta.limit == 6
