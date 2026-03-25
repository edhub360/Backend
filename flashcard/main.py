# main.py - Flashcard Microservice Backend (WITH PAGINATION)

from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession
from models import FlashcardAnalytics
from schemas import (
    FlashcardAnalyticsCreate, FlashcardAnalyticsOut,
    FlashcardDeckListItem, FlashcardDeckDetail,
    FlashcardDecksResponse, PaginationMeta,
)
from database import get_session
from models import Quiz, QuizQuestion


# ========== APP INITIALIZATION ==========
app = FastAPI(
    title="Flashcard API",
    version="1.0",
    description="Flashcard microservice using quiz data"
)


# ========== CORS MIDDLEWARE ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== ERROR HANDLERS ==========
# Must be registered BEFORE routes so FastAPI picks them up correctly

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": str(exc.detail) if hasattr(exc, "detail") else "Resource not found",
        },
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        },
    )


# ========== HEALTH CHECK ==========
@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "flashcard-api",
        "version": "1.0"
    }


@app.get("/healthz")
async def healthz(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# ========== FLASHCARD ENDPOINTS WITH PAGINATION ==========

@app.get("/flashcard-decks", response_model=dict)
async def get_flashcard_decks(
    session: AsyncSession = Depends(get_session),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(6, ge=1, le=100, description="Number of items to return (max 100)"),
):
    count_query = text("""
        SELECT COUNT(*) 
        FROM stud_hub_schema.quizzes 
        WHERE is_active = true
    """)
    total_result = await session.execute(count_query)
    total = total_result.scalar()

    query = text("""
        SELECT 
            q.quiz_id as deck_id,
            q.title,
            q.description,
            q.subject_tag,
            q.difficulty_level,
            q.is_active,
            q.estimated_time,
            COUNT(qu.question_id) as total_cards
        FROM stud_hub_schema.quizzes q
        LEFT JOIN stud_hub_schema.questions qu ON q.quiz_id = qu.quiz_id
        WHERE q.is_active = true
        GROUP BY q.quiz_id, q.title, q.description, q.subject_tag, 
                 q.difficulty_level, q.is_active, q.estimated_time
        ORDER BY q.created_at DESC
        LIMIT :limit OFFSET :offset
    """)

    result = await session.execute(query, {"limit": limit, "offset": offset})
    rows = result.fetchall()

    decks = [
        {
            "deck_id": row.deck_id,
            "title": row.title or "Untitled Deck",
            "description": row.description or "No description available",
            "subject_tag": row.subject_tag or "General",
            "difficulty_level": row.difficulty_level or "Easy",
            "is_active": row.is_active,
            "estimated_time": row.estimated_time,
            "total_cards": row.total_cards or 0,
        }
        for row in rows
    ]

    return {
        "decks": decks,
        "pagination": {
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total,
        },
    }


@app.get("/flashcard-decks/{deck_id}")
async def get_flashcard_deck_detail(
    deck_id: str,
    session: AsyncSession = Depends(get_session),
    offset: int = Query(0, ge=0, description="Number of cards to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of cards to return (max 100)"),
):
    quiz = await session.get(Quiz, deck_id)
    if not quiz:
        raise HTTPException(
            status_code=404,
            detail=f"Flashcard deck with id '{deck_id}' not found",
        )

    count_stmt = (
        select(func.count(QuizQuestion.question_id))
        .where(QuizQuestion.quiz_id == deck_id)
    )
    total_result = await session.execute(count_stmt)
    total_cards = total_result.scalar() or 0

    stmt = (
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == deck_id)
        .order_by(QuizQuestion.created_at)
        .offset(offset)
        .limit(limit)
    )

    result = await session.execute(stmt)
    questions = result.scalars().all()

    cards = [
        {
            "card_id": q.question_id,
            "front_text": q.question_text,
            "back_text": q.correct_answer,
            "hint": q.explanation,
        }
        for q in questions
    ]

    return {
        "deck_id": quiz.quiz_id,
        "title": quiz.title or "Untitled Deck",
        "description": quiz.description or "No description available",
        "subject_tag": quiz.subject_tag or "General",
        "difficulty_level": quiz.difficulty_level or "Easy",
        "estimated_time": quiz.estimated_time,
        "total_cards": total_cards,
        "cards": cards,
        "pagination": {
            "total": total_cards,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total_cards,
        },
    }


@app.post(
    "/flashcard-analytics",
    response_model=FlashcardAnalyticsOut,
    status_code=status.HTTP_201_CREATED,
)
async def log_flashcard_analytics(
    payload: FlashcardAnalyticsCreate,
    session: AsyncSession = Depends(get_session),
):
    analytics = FlashcardAnalytics(
        deck_id=payload.deck_id,
        user_id=payload.user_id,
        card_reviewed=payload.card_reviewed,
        time_taken=payload.time_taken,
    )

    session.add(analytics)
    await session.commit()
    await session.refresh(analytics)

    return FlashcardAnalyticsOut(
        analytics_id=analytics.analytics_id,
        deck_id=analytics.deck_id,
        user_id=analytics.user_id,
        card_reviewed=analytics.card_reviewed,
        time_taken=analytics.time_taken,
        reviewed_at=analytics.reviewed_at,
    )
