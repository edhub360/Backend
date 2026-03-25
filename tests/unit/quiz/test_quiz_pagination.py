import pytest
from quiz.schemas import QuizListResponse, QuizListItem
from uuid import uuid4


@pytest.mark.unit
class TestQuizPagination:

    def test_first_page(self):
        response = QuizListResponse(
            quizzes=[QuizListItem(quiz_id=str(uuid4()), title=f"Quiz {i}") for i in range(10)],
            total=50, page=1, page_size=10,
        )
        assert response.page == 1
        assert len(response.quizzes) == 10

    def test_last_page(self):
        response = QuizListResponse(
            quizzes=[QuizListItem(quiz_id=str(uuid4()), title="Quiz 1")],
            total=11, page=2, page_size=10,
        )
        assert response.page == 2
        assert len(response.quizzes) == 1

    def test_empty_results(self):
        response = QuizListResponse(
            quizzes=[], total=0, page=1, page_size=10,
        )
        assert response.total == 0
        assert len(response.quizzes) == 0

    def test_page_size_respected(self):
        response = QuizListResponse(
            quizzes=[QuizListItem(quiz_id=str(uuid4()), title=f"Q{i}") for i in range(5)],
            total=100, page=1, page_size=5,
        )
        assert response.page_size == 5
        assert len(response.quizzes) == 5
