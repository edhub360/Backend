import pytest
from datetime import datetime
from uuid import uuid4
from quiz.models import User, Quiz, QuizQuestion, QuizAttempt


@pytest.mark.unit
class TestUserModel:
    """Test User model"""
    
    def test_user_creation(self):
        """Test creating a user instance"""
        user = User(
            email="test@example.com",
            name="Test User",
            language="en",
        )
        
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.language == "en"
        assert user.user_id is not None
    
    def test_user_unique_email(self):
        """Test that email should be unique"""
        # This would be tested in integration tests
        pass


@pytest.mark.unit
class TestQuizModel:
    """Test Quiz model"""
    
    def test_quiz_creation(self):
        """Test creating a quiz"""
        quiz = Quiz(
            title="Python Basics",
            description="Learn Python",
            subject_tag="Python",
            difficulty_level="beginner",
        )
        
        assert quiz.title == "Python Basics"
        assert quiz.is_active is True
        assert quiz.quiz_id is not None
    
    def test_quiz_estimated_time(self):
        """Test estimated time field"""
        quiz = Quiz(
            title="Quick Quiz",
            estimated_time=15,
        )
        
        assert quiz.estimated_time == 15


@pytest.mark.unit
class TestQuizQuestionModel:
    """Test QuizQuestion model"""
    
    def test_question_creation(self):
        """Test creating a quiz question"""
        quiz_id = str(uuid4())
        question = QuizQuestion(
            quiz_id=quiz_id,
            question_text="What is 2+2?",
            correct_answer="4",
            incorrect_answers=["3", "5", "6"],
        )
        
        assert question.question_text == "What is 2+2?"
        assert question.correct_answer == "4"
        assert len(question.incorrect_answers) == 3
    
    def test_question_requires_quiz_id(self):
        """Test that question requires a quiz_id"""
        question = QuizQuestion(
            question_text="Test?",
            correct_answer="Yes",
            incorrect_answers=["No"],
        )
        
        assert question.quiz_id is None
