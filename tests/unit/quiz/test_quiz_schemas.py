import pytest
from uuid import uuid4
import pydantic


@pytest.mark.unit
class TestUserSchemas:

    def test_user_create_valid(self):
        from quiz.schemas import UserCreate
        user = UserCreate(email="test@example.com", name="Test User")
        assert user.email == "test@example.com"

    def test_user_create_invalid_email(self):
        from quiz.schemas import UserCreate
        with pytest.raises(pydantic.ValidationError):
            UserCreate(email="not-an-email")

    def test_user_update_partial(self):
        from quiz.schemas import UserUpdate
        update = UserUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.language is None

    def test_user_update_all_fields_optional(self):
        from quiz.schemas import UserUpdate
        update = UserUpdate()
        assert update.name is None
        assert update.subscription_tier is None


@pytest.mark.unit
class TestQuizSchemas:

    def test_quiz_create_valid(self):
        from quiz.schemas import QuizCreate, QuizQuestionCreate
        quiz = QuizCreate(
            title="Python Quiz",
            subject_tag="Python",
            questions=[
                QuizQuestionCreate(
                    question_text="What is Python?",
                    correct_answer="A language",
                    incorrect_answers=["A snake", "A drink"],
                )
            ],
        )
        assert quiz.title == "Python Quiz"
        assert len(quiz.questions) == 1
        assert quiz.is_active is True

    def test_quiz_create_requires_title(self):
        from quiz.schemas import QuizCreate
        with pytest.raises(pydantic.ValidationError):
            QuizCreate(questions=[])

    def test_quiz_question_empty_incorrect_answers_default(self):
        from quiz.schemas import QuizQuestionCreate
        q = QuizQuestionCreate(question_text="Test?", correct_answer="Yes")
        assert q.incorrect_answers == []

    def test_quiz_list_item_defaults(self):
        from quiz.schemas import QuizListItem
        item = QuizListItem(quiz_id=str(uuid4()), title="Test Quiz")
        assert item.total_questions == 0
        assert item.is_active is True

    def test_quiz_list_response_structure(self):
        from quiz.schemas import QuizListResponse, QuizListItem
        response = QuizListResponse(
            quizzes=[QuizListItem(quiz_id=str(uuid4()), title="Quiz 1")],
            total=1, page=1, page_size=10,
        )
        assert response.total == 1
        assert len(response.quizzes) == 1


@pytest.mark.unit
class TestQuizAttemptSchemas:

    def test_attempt_create_valid(self):
        from quiz.schemas import QuizAttemptCreate
        attempt = QuizAttemptCreate(
            user_id=str(uuid4()), quiz_id=str(uuid4()),
            score=8, total_questions=10,
            score_percentage=80.0, time_taken=120,
        )
        assert attempt.score == 8
        assert attempt.score_percentage == 80.0

    def test_attempt_create_missing_fields_raises(self):
        from quiz.schemas import QuizAttemptCreate
        with pytest.raises(pydantic.ValidationError):
            QuizAttemptCreate(user_id=str(uuid4()))

    def test_answer_detail_valid(self):
        from quiz.schemas import AnswerDetail
        answer = AnswerDetail(
            question_id=str(uuid4()),
            user_answer="A language",
            is_correct=True,
        )
        assert answer.is_correct is True

    def test_attempt_answers_optional(self):
        from quiz.schemas import QuizAttemptCreate
        attempt = QuizAttemptCreate(
            user_id=str(uuid4()), quiz_id=str(uuid4()),
            score=5, total_questions=10,
            score_percentage=50.0, time_taken=60,
        )
        assert attempt.answers is None
