from datetime import timezone
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session, engine
from models import Base, User, QuizQuestion, Quiz, QuizAttempt, UserStudyStats  # FIXED: Changed Question to QuizQuestion
from schemas import (
    UserCreate, UserUpdate, UserOut,
    QuestionCreate, QuestionOut,
    QuizCreate, QuizOut,  # Legacy
    QuizListItem, QuizDetail, QuizQuestionResponse,
    QuizAttemptCreate, QuizAttemptResponse,
    UserQuizHistory, QuizStatistics, QuizDashboardSummary
)

from .study_stats import update_user_study_stats
app = FastAPI(title="Quiz API (PostgreSQL + SQLAlchemy async)", version="3.0")

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
    return {"status": "ok", "db": "postgresql", "orm": "sqlalchemy-async", "version": "3.0"}

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

# ---------------- Quizzes (NEW API) ----------------

@app.get("/quizzes", response_model=List[QuizListItem])
async def list_quizzes(session: AsyncSession = Depends(get_session)):
    """Get all active quizzes (global, no user_id needed)"""
    query = text("""
        SELECT 
            q.quiz_id,
            q.title,
            q.description,
            q.subject_tag,
            q.difficulty_level,
            q.estimated_time,
            q.is_active,
            COUNT(qu.question_id) as total_questions
        FROM stud_hub_schema.quizzes q
        LEFT JOIN stud_hub_schema.questions qu ON q.quiz_id = qu.quiz_id
        WHERE q.is_active = true
        GROUP BY q.quiz_id
        ORDER BY q.created_at DESC
    """)
    
    result = await session.execute(query)
    rows = result.fetchall()
    
    return [
        QuizListItem(
            quiz_id=str(row.quiz_id),
            title=row.title or f"Quiz #{str(row.quiz_id)[:8]}",
            description=row.description,
            subject_tag=row.subject_tag,
            difficulty_level=row.difficulty_level,
            estimated_time=row.estimated_time,
            total_questions=row.total_questions or 0,
            is_active=row.is_active
        )
        for row in rows
    ]

@app.get("/quizzes/{quiz_id}", response_model=QuizDetail)
async def get_quiz_detail(quiz_id: str, session: AsyncSession = Depends(get_session)):
    """Get quiz with all questions"""
    # Get quiz
    quiz = await session.get(Quiz, quiz_id)
    if not quiz or not quiz.is_active:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Get questions - FIXED: Changed Question to QuizQuestion
    stmt = select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.created_at)
    result = await session.execute(stmt)
    questions = result.scalars().all()
    
    return QuizDetail(
        quiz_id=str(quiz.quiz_id),
        title=quiz.title or f"Quiz #{quiz_id[:8]}",
        description=quiz.description,
        subject_tag=quiz.subject_tag,
        difficulty_level=quiz.difficulty_level,
        estimated_time=quiz.estimated_time,
        questions=[
            QuizQuestionResponse(
                question_id=str(q.question_id),
                question_text=q.question_text or "",
                correct_answer=q.correct_answer or "",
                incorrect_answers=q.incorrect_answers or [],
                explanation=q.explanation,
                difficulty=q.difficulty
            )
            for q in questions
        ]
    )

@app.post("/quiz-attempts", response_model=QuizAttemptResponse, status_code=status.HTTP_201_CREATED)
async def submit_quiz_attempt(payload: QuizAttemptCreate, session: AsyncSession = Depends(get_session)):
    """Submit a quiz attempt and save results"""
    # Verify user exists
    user = await session.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify quiz exists
    quiz = await session.get(Quiz, payload.quiz_id)
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Create attempt
    attempt = QuizAttempt(
        user_id=payload.user_id,
        quiz_id=payload.quiz_id,
        score=payload.score,
        total_questions=payload.total_questions,
        score_percentage=payload.score_percentage,
        time_taken=payload.time_taken,
        answers=[a.model_dump() for a in payload.answers] if payload.answers else None
    )
    session.add(attempt)
    await session.flush()  # get completed_at filled by DB default

    # Derive study_date from completed_at (UTC for now)
    study_date = attempt.completed_at.astimezone(timezone.utc).date()

    await update_user_study_stats(
        db=session,
        user_id=attempt.user_id,
        time_taken_seconds=attempt.time_taken,
        study_date=study_date,
    )
    
    await session.commit()
    await session.refresh(attempt)
    
    return QuizAttemptResponse(
        attempt_id=str(attempt.attempt_id),
        user_id=str(attempt.user_id),
        quiz_id=str(attempt.quiz_id),
        score=attempt.score,
        total_questions=attempt.total_questions,
        score_percentage=attempt.score_percentage,
        time_taken=attempt.time_taken,
        completed_at=attempt.completed_at
    )

@app.get("/users/{user_id}/quiz-attempts", response_model=List[UserQuizHistory])
async def get_user_quiz_history(user_id: str, limit: int = 50, session: AsyncSession = Depends(get_session)):
    """Get user's quiz attempt history"""
    query = text("""
        SELECT * FROM stud_hub_schema.user_quiz_history
        WHERE user_id = :user_id
        ORDER BY completed_at DESC
        LIMIT :limit
    """)
    
    result = await session.execute(query, {"user_id": user_id, "limit": limit})
    rows = result.fetchall()
    
    return [
        UserQuizHistory(
            attempt_id=str(row.attempt_id),
            quiz_id=str(row.quiz_id),
            quiz_title=row.quiz_title,
            subject_tag=row.subject_tag,
            difficulty_level=row.difficulty_level,
            score=row.score,
            total_questions=row.total_questions,
            score_percentage=row.score_percentage,
            time_taken=row.time_taken,
            completed_at=row.completed_at
        )
        for row in rows
    ]

@app.get("/quiz-statistics", response_model=List[QuizStatistics])
async def get_quiz_statistics(session: AsyncSession = Depends(get_session)):
    """Get aggregated quiz performance statistics"""
    query = text("SELECT * FROM stud_hub_schema.quiz_statistics")
    result = await session.execute(query)
    rows = result.fetchall()
    
    return [
        QuizStatistics(
            quiz_id=str(row.quiz_id),
            title=row.title,
            total_users_attempted=row.total_users_attempted or 0,
            total_attempts=row.total_attempts or 0,
            average_score=float(row.average_score) if row.average_score else None,
            highest_score=float(row.highest_score) if row.highest_score else None,
            lowest_score=float(row.lowest_score) if row.lowest_score else None,
            average_time=float(row.average_time) if row.average_time else None
        )
        for row in rows
    ]

# ---------------- Legacy Quiz Endpoints (Deprecated) ----------------
@app.post("/quizzes/legacy", response_model=QuizOut, status_code=status.HTTP_201_CREATED)
async def create_quiz_legacy(payload: QuizCreate, session: AsyncSession = Depends(get_session)):
    """Legacy endpoint - use POST /quiz-attempts instead"""
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



@app.get("/dashboard/summary", response_model=QuizDashboardSummary)
async def get_quiz_dashboard_summary(user_id: str, session: AsyncSession = Depends(get_session)):
    # 1) Ensure user exists (reuse logic from submit_quiz_attempt)
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 2) Average score across all attempts
    avg_stmt = (
        select(func.coalesce(func.avg(QuizAttempt.score_percentage), 0.0))
        .where(QuizAttempt.user_id == user_id)
    )

    # 3) Study time today from quiz_attempts (UTC day for now)
    start_today = func.date_trunc("day", func.now())
    end_today = start_today + func.interval("1 day")

    today_stmt = (
        select(func.coalesce(func.sum(QuizAttempt.time_taken), 0))
        .where(QuizAttempt.user_id == user_id)
        .where(QuizAttempt.completed_at >= start_today)
        .where(QuizAttempt.completed_at < end_today)
    )

    # 4) Total time + streak from user_study_stats
    stats_stmt = (
        select(
            UserStudyStats.total_study_seconds,
            UserStudyStats.current_streak_days,
        )
        .where(UserStudyStats.user_id == user_id)
    )

    avg_res = await session.execute(avg_stmt)
    today_res = await session.execute(today_stmt)
    stats_res = await session.execute(stats_stmt)

    avg_percent = float(avg_res.scalar_one() or 0.0)
    study_today = int(today_res.scalar_one() or 0)

    stats_row = stats_res.one_or_none()
    if stats_row:
        total_study_seconds, current_streak_days = stats_row
    else:
        total_study_seconds, current_streak_days = 0, 0

    return QuizDashboardSummary(
        user_id=user_id,
        averageScorePercent=round(avg_percent, 2),
        studyTimeSecondsToday=study_today,
        totalStudySeconds=int(total_study_seconds or 0),
        currentStreakDays=int(current_streak_days or 0),
    )
