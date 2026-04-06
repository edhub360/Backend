# quiz/study_stats.py
from datetime import timedelta, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quiz.models import UserStudyStats


async def update_user_study_stats(
    db: AsyncSession,
    user_id: str,
    time_taken_seconds: int,
    study_date: date,
) -> None:
    result = await db.execute(
        select(UserStudyStats).where(UserStudyStats.user_id == user_id).with_for_update()
    )
    row = result.scalar_one_or_none()

    if row is None:
        row = UserStudyStats(
            user_id=user_id,
            total_study_seconds=time_taken_seconds,
            current_streak_days=1,
            longest_streak_days=1,
            last_study_date=study_date,
        )
        db.add(row)
        await db.commit()  # ← was missing
        return

    # Update total time
    row.total_study_seconds += time_taken_seconds

    # Streak logic
    last_date = row.last_study_date
    if last_date is None or study_date > last_date + timedelta(days=1):
        # Streak broken
        row.current_streak_days = 1
    elif study_date == last_date:
        # Same day — no streak change
        pass
    else:
        # Consecutive day
        row.current_streak_days += 1

    # Only update longest when current exceeds it (never on reset)
    if row.current_streak_days > row.longest_streak_days:
        row.longest_streak_days = row.current_streak_days

    row.last_study_date = study_date
    await db.commit()  # ← was missing
