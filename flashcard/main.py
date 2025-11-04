# main.py
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session, engine
from models import Base, User, Question, Quiz, Flashcard
from schemas import (
    UserCreate, UserUpdate, UserOut,
    QuestionCreate, QuestionOut,
    QuizCreate, QuizOut,
    FlashcardCreate, FlashcardOut
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

# CRUD endpoints
@app.post("/flashcards", response_model=FlashcardOut)
async def create_flashcard(flashcard: FlashcardCreate, session: AsyncSession = Depends(get_session)):
    db_flashcard = Flashcard(**flashcard.dict())
    session.add(db_flashcard)
    await session.commit()
    await session.refresh(db_flashcard)
    return db_flashcard

@app.get("/flashcards", response_model=List[FlashcardOut])
async def list_flashcards(user_id: Optional[str] = None, session: AsyncSession = Depends(get_session)):
    stmt = session.query(Flashcard)
    if user_id:
        stmt = stmt.filter(Flashcard.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalars().all()

@app.get("/flashcards/{card_id}", response_model=FlashcardOut)
async def get_flashcard(card_id: str, session: AsyncSession = Depends(get_session)):
    db_flashcard = await session.get(Flashcard, card_id)
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    return db_flashcard

@app.patch("/flashcards/{card_id}", response_model=FlashcardOut)
async def update_flashcard(card_id: str, flashcard: FlashcardCreate, session: AsyncSession = Depends(get_session)):
    db_flashcard = await session.get(Flashcard, card_id)
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    for key, value in flashcard.dict(exclude_unset=True).items():
        setattr(db_flashcard, key, value)
    await session.commit()
    await session.refresh(db_flashcard)
    return db_flashcard

@app.delete("/flashcards/{card_id}")
async def delete_flashcard(card_id: str, session: AsyncSession = Depends(get_session)):
    db_flashcard = await session.get(Flashcard, card_id)
    if not db_flashcard:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    await session.delete(db_flashcard)
    await session.commit()
    return {"message": "Flashcard deleted successfully"}