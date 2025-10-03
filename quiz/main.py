# main.py
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session, engine
from models import Base, User, Question, Quiz, Response
from schemas import (
    UserCreate, UserUpdate, UserOut,
    QuestionCreate, QuestionOut,
    QuizCreate, QuizOut,
    ResponseCreate, ResponseOut
)

app = FastAPI(title="Quiz API (PostgreSQL + SQLAlchemy async)", version="2.0")

# CORS for React apps (tighten in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: create tables in dev (for production, manage via Alembic)
# Uncomment if you want auto-create on startup locally.
#@app.on_event("startup")
#async def on_startup():
#    async with engine.begin() as conn:
#        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    return {"status": "ok", "db": "postgresql", "orm": "sqlalchemy-async"}

# ---------------- Health ----------------
@app.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_session)):
    try:
        result = await session.execute(select(User).limit(1))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}

# ---------------- Users ----------------
@app.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    user = User(**payload.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

@app.get("/users", response_model=List[UserOut])
async def list_users(limit: int = 100, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).limit(limit))
    return result.scalars().all()

@app.get("/users/{user_id}", response_model=UserOut)
async def get_user(user_id: str, session: AsyncSession = Depends(get_session)):
    obj = await session.get(User, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    return obj

@app.patch("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: str, payload: UserUpdate, session: AsyncSession = Depends(get_session)):
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
    obj = await session.get(User, user_id)
    if not obj:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(obj)
    await session.commit()
    return

# ---------------- Questions ----------------
@app.post("/questions", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(payload: QuestionCreate, session: AsyncSession = Depends(get_session)):
    question = Question(**payload.model_dump())
    session.add(question)
    await session.commit()
    await session.refresh(question)
    return question

@app.get("/questions", response_model=List[QuestionOut])
async def list_questions(user_id: Optional[str] = None, limit: int = 100, session: AsyncSession = Depends(get_session)):
    stmt = select(Question).limit(limit)
    if user_id:
        stmt = select(Question).where(Question.user_id == user_id).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()

@app.get("/questions/{question_id}", response_model=QuestionOut)
async def get_question(question_id: str, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Question, question_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Question not found")
    return obj

# ---------------- Quizzes ----------------
@app.post("/quizzes", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def create_quiz(payload: QuizCreate, session: AsyncSession = Depends(get_session)):
    quiz = Quiz(
        user_id=payload.user_id,
        questions=[q.model_dump() for q in payload.questions] if payload.questions else None,
        score=payload.score,
        time_taken=payload.time_taken,
    )
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)
    return quiz

@app.get("/quizzes", response_model=List[QuizOut])
async def list_quizzes(user_id: Optional[str] = None, limit: int = 100, session: AsyncSession = Depends(get_session)):
    stmt = select(Quiz).limit(limit)
    if user_id:
        stmt = select(Quiz).where(Quiz.user_id == user_id).limit(limit)
    result = await session.execute(stmt)
    quizzes = result.scalars().all()

    # Transform DB JSON → schema format
    for quiz in quizzes:
        if quiz.questions:
            quiz.questions = [
                {
                    "question": q.get("question_text"),
                    "options": q.get("options"),
                    "correct": q.get("correct_answer_index"),
                    "explanation": q.get("explanation")
                }
                for q in quiz.questions
            ]
    return quizzes

#@app.get("/quizzes", response_model=List[QuizOut])
#async def list_quizzes(user_id: Optional[str] = None, limit: int = 100, session: AsyncSession = Depends(get_session)):
#    stmt = select(Quiz).limit(limit)
#    if user_id:
#        stmt = select(Quiz).where(Quiz.user_id == user_id).limit(limit)
#    result = await session.execute(stmt)
#    return result.scalars().all()

@app.get("/quizzes/{quiz_id}", response_model=QuizOut)
async def get_quiz(quiz_id: str, session: AsyncSession = Depends(get_session)):
    obj = await session.get(Quiz, quiz_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return obj

