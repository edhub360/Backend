import pytest
from uuid import uuid4


@pytest.mark.unit
class TestUserModel:

    def test_user_creation_basic(self):
        from quiz.models import User
        user = User(email="test@example.com", name="Test User", language="en")
        assert user.email == "test@example.com"
        assert user.name == "Test User"

    def test_user_id_default_configured(self):
        from quiz.models import User
        col = User.__table__.c.user_id
        assert col.default is not None

    def test_two_users_have_different_ids(self):
        from quiz.models import User
        u1 = User(email="a@example.com")
        u2 = User(email="b@example.com")
        u1.user_id = str(uuid4())
        u2.user_id = str(uuid4())
        assert u1.user_id != u2.user_id

    def test_user_optional_fields_default_none(self):
        from quiz.models import User
        user = User(email="test@example.com")
        assert user.name is None
        assert user.language is None
        assert user.subscription_tier is None
        assert user.study_goals is None
        assert user.device_info is None


@pytest.mark.unit
class TestQuizModel:

    def test_quiz_creation(self):
        from quiz.models import Quiz
        quiz = Quiz(title="Python Basics", subject_tag="Python", difficulty_level="beginner")
        assert quiz.title == "Python Basics"
        assert quiz.subject_tag == "Python"

    def test_quiz_is_active_default_configured(self):
        from quiz.models import Quiz
        col = Quiz.__table__.c.is_active
        assert col.default.arg is True

    def test_quiz_id_default_configured(self):
        from quiz.models import Quiz
        col = Quiz.__table__.c.quiz_id
        assert col.default is not None

    def test_quiz_optional_fields_default_none(self):
        from quiz.models import Quiz
        quiz = Quiz(title="Test")
        assert quiz.description is None
        assert quiz.estimated_time is None
        assert quiz.tags is None
        assert quiz.quiz_metadata is None

    def test_quiz_with_estimated_time(self):
        from quiz.models import Quiz
        quiz = Quiz(title="Timed Quiz", estimated_time=30)
        assert quiz.estimated_time == 30

    def test_two_quizzes_have_different_ids(self):
        from quiz.models import Quiz
        q1 = Quiz(title="A")
        q2 = Quiz(title="B")
        q1.quiz_id = str(uuid4())
        q2.quiz_id = str(uuid4())
        assert q1.quiz_id != q2.quiz_id


@pytest.mark.unit
class TestQuizQuestionModel:

    def test_question_creation(self):
        from quiz.models import QuizQuestion
        q = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="What is FastAPI?",
            correct_answer="A web framework",
            incorrect_answers=["A database", "A cloud service", "An OS"],
        )
        assert q.question_text == "What is FastAPI?"
        assert q.correct_answer == "A web framework"
        assert len(q.incorrect_answers) == 3

    def test_question_id_default_configured(self):
        from quiz.models import QuizQuestion
        col = QuizQuestion.__table__.c.question_id
        assert col.default is not None

    def test_two_questions_have_different_ids(self):
        from quiz.models import QuizQuestion
        qid = str(uuid4())
        q1 = QuizQuestion(quiz_id=qid, question_text="Q1?", correct_answer="A", incorrect_answers=[])
        q2 = QuizQuestion(quiz_id=qid, question_text="Q2?", correct_answer="B", incorrect_answers=[])
        q1.question_id = str(uuid4())
        q2.question_id = str(uuid4())
        assert q1.question_id != q2.question_id

    def test_question_optional_fields_default_none(self):
        from quiz.models import QuizQuestion
        q = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="Test?",
            correct_answer="Yes",
            incorrect_answers=["No"],
        )
        assert q.explanation is None
        assert q.difficulty is None
        assert q.subject_tag is None

    def test_question_without_quiz_id_is_none(self):
        from quiz.models import QuizQuestion
        q = QuizQuestion(question_text="Test?", correct_answer="Yes", incorrect_answers=["No"])
        assert q.quiz_id is None

    def test_question_with_explanation(self):
        from quiz.models import QuizQuestion
        q = QuizQuestion(
            quiz_id=str(uuid4()),
            question_text="What is Python?",
            correct_answer="A language",
            incorrect_answers=["A snake"],
            explanation="Python is a high-level language",
        )
        assert q.explanation == "Python is a high-level language"


@pytest.mark.unit
class TestQuizAttemptModel:

    def test_attempt_creation(self):
        from quiz.models import QuizAttempt
        attempt = QuizAttempt(
            user_id=str(uuid4()),
            quiz_id=str(uuid4()),
            score=8,
            total_questions=10,
            score_percentage=80.0,
            time_taken=120,
        )
        assert attempt.score == 8
        assert attempt.total_questions == 10
        assert attempt.score_percentage == 80.0
        assert attempt.time_taken == 120

    def test_attempt_id_default_configured(self):
        from quiz.models import QuizAttempt
        col = QuizAttempt.__table__.c.attempt_id
        assert col.default is not None

    def test_attempt_answers_optional(self):
        from quiz.models import QuizAttempt
        attempt = QuizAttempt(
            user_id=str(uuid4()),
            quiz_id=str(uuid4()),
            score=5,
            total_questions=10,
            score_percentage=50.0,
            time_taken=60,
        )
        assert attempt.answers is None

    def test_two_attempts_have_different_ids(self):
        from quiz.models import QuizAttempt
        a1 = QuizAttempt(user_id=str(uuid4()), quiz_id=str(uuid4()), score=5,
                         total_questions=10, score_percentage=50.0, time_taken=60)
        a2 = QuizAttempt(user_id=str(uuid4()), quiz_id=str(uuid4()), score=8,
                         total_questions=10, score_percentage=80.0, time_taken=90)
        a1.attempt_id = str(uuid4())
        a2.attempt_id = str(uuid4())
        assert a1.attempt_id != a2.attempt_id


@pytest.mark.unit
class TestUserStudyStatsModel:

    def test_stats_creation(self):
        from quiz.models import UserStudyStats
        stats = UserStudyStats(
            user_id=str(uuid4()),
            total_study_seconds=3600,
            current_streak_days=5,
            longest_streak_days=10,
        )
        assert stats.total_study_seconds == 3600
        assert stats.current_streak_days == 5
        assert stats.longest_streak_days == 10

    def test_stats_total_seconds_default_configured(self):
        from quiz.models import UserStudyStats
        col = UserStudyStats.__table__.c.total_study_seconds
        assert col.default.arg == 0

    def test_stats_streak_defaults_configured(self):
        from quiz.models import UserStudyStats
        cols = UserStudyStats.__table__.c
        assert cols.current_streak_days.default.arg == 0
        assert cols.longest_streak_days.default.arg == 0

    def test_stats_last_study_date_optional(self):
        from quiz.models import UserStudyStats
        stats = UserStudyStats(user_id=str(uuid4()))
        assert stats.last_study_date is None
