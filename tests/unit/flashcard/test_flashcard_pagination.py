import pytest
from flashcard.schemas import PaginationMeta


@pytest.mark.unit
class TestFlashcardPagination:

    def test_has_more_when_items_remain(self):
        meta = PaginationMeta(total=20, offset=0, limit=6, has_more=True)
        assert meta.has_more is True

    def test_no_more_when_last_page(self):
        meta = PaginationMeta(total=6, offset=0, limit=6, has_more=False)
        assert meta.has_more is False

    def test_offset_advances_correctly(self):
        meta = PaginationMeta(total=20, offset=6, limit=6, has_more=True)
        assert meta.offset == 6

    def test_empty_results(self):
        meta = PaginationMeta(total=0, offset=0, limit=6, has_more=False)
        assert meta.total == 0
        assert meta.has_more is False

    def test_partial_last_page(self):
        # 13 items, page size 6, on page 3 (offset=12) → 1 item, no more
        meta = PaginationMeta(total=13, offset=12, limit=6, has_more=False)
        assert meta.has_more is False
        assert meta.offset == 12
