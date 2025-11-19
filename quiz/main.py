from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload  # Import this for eager loading
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session, engine
from models import Base, User, Question, Quiz
from schemas import (
    UserCreate, UserUpdate, UserOut,
    QuestionCreate, QuestionOut,
    QuizCreate, QuizOut
)

app = FastAPI(title="Quiz API (PostgreSQL + SQLAlchemy async)", version="2.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Quiz API is running", "db": "postgresql", "orm": "sqlalchemy-async"}

# ---------------- Health Check ----------------
@app.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(User).limit(1))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ============================================
# USER ENDPOINTS
# ============================================

@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    """Create a new user"""
    user = User(**payload.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@app.get("/users", response_model=List[UserOut])
async def list_users(limit: int = 100, session: AsyncSession = Depends(get_session)):
    """List all users"""
    result = await session.execute(select(User).limit(limit))
    return result.scalars().all()

@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: str, session: AsyncSession = Depends(get_session)):
    """Get user by ID"""
    obj = await session.get(User, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@app.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, session: AsyncSession = Depends(get_session)):
    """Update user details"""
    obj = await session.get(User, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj

@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a user"""
    obj = await session.get(User, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(obj)
    await session.commit()
    return

# ============================================
# QUIZ ENDPOINTS
# ============================================

@app.post("/quizzes", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def create_quiz(payload: QuizCreate, session: AsyncSession = Depends(get_session)):
    """Create a new quiz"""
    quiz = Quiz(**payload.model_dump())
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)
    return quiz

@app.get("/quizzes/user/{user_id}", response_model=List[QuizOut])
async def get_user_quizzes(user_id: str, session: AsyncSession = Depends(get_session)):
    """Get all quizzes for a specific user with their questions (eager loaded)"""
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.questions))  # Eagerly load questions
        .where(Quiz.user_id == user_id)
        .order_by(Quiz.created_at.desc())
    )
    result = await session.execute(stmt)
    quizzes = result.scalars().all()
    return quizzes

@app.get("/quizzes", response_model=List[QuizOut])
async def list_quizzes(
    user_id: Optional[str] = None, 
    limit: int = 100, 
    session: AsyncSession = Depends(get_session)
):
    """List all quizzes (optionally filtered by user_id)"""
    stmt = select(Quiz).options(selectinload(Quiz.questions)).limit(limit)
    if user_id:
        stmt = stmt.where(Quiz.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()

@app.get("/quizzes/{quiz_id}", response_model=QuizOut)
async def get_quiz(quiz_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific quiz with its questions"""
    stmt = (
        select(Quiz)
        .options(selectinload(Quiz.questions))
        .where(Quiz.quiz_id == quiz_id)
    )
    result = await session.execute(stmt)
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz

@app.delete("/quizzes/{quiz_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quiz(quiz_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a quiz (cascades to questions)"""
    obj = await session.get(Quiz, quiz_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Quiz not found")
    await session.delete(obj)
    await session.commit()
    return

# ============================================
# QUESTION ENDPOINTS
# ============================================

@app.post("/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(payload: QuestionCreate, session: AsyncSession = Depends(get_session)):
    """Create a new question for a quiz"""
    question = Question(**payload.model_dump())
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question

@app.get("/quizzes/{quiz_id}/questions", response_model=List[QuestionOut])
async def get_quiz_questions(quiz_id: str, session: AsyncSession = Depends(get_session)):
    """Get all questions for a specific quiz"""
    stmt = select(Question).where(Question.quiz_id == quiz_id).order_by(Question.created_at)
    result = await session.execute(stmt)
    return result.scalars().all()

@app.get("/questions", response_model=List[QuestionOut])
async def list_questions(
    user_id: Optional[str] = None, 
    quiz_id: Optional[str] = None,
    limit: int = 100, 
    session: AsyncSession = Depends(get_session)
):
    """List all questions (optionally filtered by user_id or quiz_id)"""
    stmt = select(Question).limit(limit)
    if user_id:
        stmt = stmt.where(Question.user_id == user_id)
    if quiz_id:
        stmt = stmt.where(Question.quiz_id == quiz_id)
    result = await session.execute(stmt)
    return result.scalars().all()

@app.get("/questions/{question_id}", response_model=QuestionOut)
async def get_question(question_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific question"""
    obj = await session.get(Question, question_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Question not found")
    return obj

@app.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(question_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a specific question"""
    obj = await session.get(Question, question_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Question not found")
    await session.delete(obj)
    await session.commit()
    return
