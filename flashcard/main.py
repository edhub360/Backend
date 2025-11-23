# main.py - Flashcard Microservice Backend
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Quiz, QuizQuestion

# ========== APP INITIALIZATION ==========
app = FastAPI(
    title="Flashcard API", 
    version="1.0",
    description="Standalone flashcard microservice using quiz data"
)

# ========== CORS MIDDLEWARE ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    """Health check endpoint"""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

# ========== FLASHCARD ENDPOINTS ==========

@app.get("/flashcard-decks", response_model=List[dict])
async def get_flashcard_decks(session: AsyncSession = Depends(get_session)):
    """
    Get all active flashcard decks (quizzes).
    Returns list of decks with card counts.
    """
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
    """)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    return [
        {
            "deck_id": row.deck_id,
            "title": row.title or "Untitled Deck",
            "description": row.description or "No description available",
            "subject_tag": row.subject_tag or "General",
            "difficulty_level": row.difficulty_level or "Easy",
            "is_active": row.is_active,
            "estimated_time": row.estimated_time,
            "total_cards": row.total_cards or 0
        }
        for row in rows
    ]


@app.get("/flashcard-decks/{deck_id}")
async def get_flashcard_deck_detail(
    deck_id: str, 
    session: AsyncSession = Depends(get_session)
):
    """
    Get flashcard deck with all cards.
    Returns deck info + all flashcards (questions as front/back cards).
    """
    # Get quiz (deck)
    quiz = await session.get(Quiz, deck_id)
    if not quiz:
        raise HTTPException(
            status_code=404, 
            detail=f"Flashcard deck with id '{deck_id}' not found"
        )
    
    # Get all questions (cards) for this deck
    stmt = (
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == deck_id)
        .order_by(QuizQuestion.created_at)
    )
    result = await session.execute(stmt)
    questions = result.scalars().all()
    
    # Map questions to flashcard format
    cards = [
        {
            "card_id": q.question_id,
            "front_text": q.question_text,  # Question/Term
            "back_text": q.correct_answer,   # Answer/Definition
            "hint": q.explanation            # Optional hint
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
        "total_cards": len(cards),
        "cards": cards
    }


# ========== ERROR HANDLERS ==========
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {
        "error": "Not Found",
        "message": str(exc.detail) if hasattr(exc, 'detail') else "Resource not found"
    }

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred"
    }
