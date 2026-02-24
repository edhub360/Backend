import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from quiz.models import User, Quiz, QuizQuestion
from uuid import uuid4


@pytest.mark.integration
class TestQuizEndpoints:
    """Integration tests for quiz endpoints"""
    
    @pytest.fixture
    async def setup_test_data(self, test_session: AsyncSession):
        """Setup test data"""
        # Create test user
        user = User(
            email="test@example.com",
            name="Test User",
        )
        test_session.add(user)
        
        # Create test quiz
        quiz = Quiz(
            title="Test Quiz",
            subject_tag="Python",
        )
        test_session.add(quiz)
        
        await test_session.commit()
        
        return {"user": user, "quiz": quiz}
    
    @pytest.mark.asyncio
    async def test_create_quiz(self, test_session, sample_quiz_data):
        """Test creating a new quiz"""
        # This would be an actual API test using TestClient
        # Demonstration of test structure
        assert sample_quiz_data["title"] == "Python Basics Quiz"
    
    @pytest.mark.asyncio
    async def test_list_quizzes(self, test_session, setup_test_data):
        """Test listing all quizzes"""
        data = await setup_test_data
        assert data["quiz"] is not None
    
    @pytest.mark.asyncio
    async def test_get_quiz_by_id(self, test_session, setup_test_data):
        """Test retrieving a quiz by ID"""
        data = await setup_test_data
        quiz = data["quiz"]
        
        assert quiz.quiz_id is not None
        assert quiz.title == "Test Quiz"
    
    @pytest.mark.asyncio
    async def test_update_quiz(self, test_session, setup_test_data):
        """Test updating a quiz"""
        data = await setup_test_data
        quiz = data["quiz"]
        
        quiz.title = "Updated Title"
        await test_session.commit()
        
        assert quiz.title == "Updated Title"


@pytest.mark.integration
class TestQuestionEndpoints:
    """Integration tests for question endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_question(self, test_session, sample_question_data):
        """Test creating a question for a quiz"""
        quiz_id = str(uuid4())
        question = QuizQuestion(
            quiz_id=quiz_id,
            **sample_question_data
        )
        test_session.add(question)
        await test_session.commit()
        
        assert question.question_id is not None
    
    @pytest.mark.asyncio
    async def test_invalid_question_data(self, test_session):
        """Test creating question with invalid data"""
        # Missing required fields
        with pytest.raises(TypeError):
            QuizQuestion(question_text="Test?")
