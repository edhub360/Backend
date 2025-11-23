# main.py (ADD THESE ENDPOINTS TO YOUR EXISTING FILE)

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

# ========== FLASHCARD ENDPOINTS (Reusing Quiz/Question tables) ==========

@app.get("/flashcard-decks", response_model=List[dict])
async def get_flashcard_decks(session: AsyncSession = Depends(get_session)):
    """
    Get all active quizzes as flashcard decks.
    Reuses the quizzes table structure.
    """
    from sqlalchemy import text
    
    query = text("""
        SELECT 
            q.quiz_id as deck_id,
            q.title,
            q.description,
            q.subject_tag,
            q.difficulty_level,
            q.is_active,
            COUNT(qu.question_id) as total_cards
        FROM stud_hub_schema.quizzes q
        LEFT JOIN stud_hub_schema.questions qu ON q.quiz_id = qu.quiz_id
        WHERE q.is_active = true
        GROUP BY q.quiz_id
        ORDER BY q.created_at DESC
    """)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    return [
        {
            "deck_id": row.deck_id,
            "title": row.title or "Untitled Deck",
            "description": row.description or "",
            "subject_tag": row.subject_tag or "General",
            "difficulty_level": row.difficulty_level or "Easy",
            "is_active": row.is_active,
            "total_cards": row.total_cards or 0
        }
        for row in rows
    ]


@app.get("/flashcard-decks/{deck_id}", response_model=dict)
async def get_flashcard_deck_detail(
    deck_id: str, 
    session: AsyncSession = Depends(get_session)
):
    """
    Get flashcard deck with all cards.
    Reuses quiz + questions table.
    """
    # Get quiz (deck)
    quiz = await session.get(Quiz, deck_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Deck not found")
    
    # Get all questions (cards) for this quiz
    stmt = (
        select(QuizQuestion)
        .where(QuizQuestion.quiz_id == deck_id)
        .order_by(QuizQuestion.created_at)
    )
    result = await session.execute(stmt)
    questions = result.scalars().all()
    
    # Map to flashcard format
    cards = [
        {
            "card_id": q.question_id,
            "front_text": q.question_text,
            "back_text": q.correct_answer,
            "hint": q.explanation
        }
        for q in questions
    ]
    
    return {
        "deck_id": quiz.quiz_id,
        "title": quiz.title or "Untitled Deck",
        "description": quiz.description or "",
        "subject_tag": quiz.subject_tag or "General",
        "difficulty_level": quiz.difficulty_level or "Easy",
        "cards": cards
    }
