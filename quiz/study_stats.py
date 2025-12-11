# study_stats.py
from datetime import timedelta, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UserStudyStats


async def update_user_study_stats(
    db: AsyncSession,
    user_id: str,
    time_taken_seconds: int,
    study_date: date,
) -> None:
    # Lock row if exists
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
        return

    # Update total time
    row.total_study_seconds += time_taken_seconds

    # Streak logic
    last_date = row.last_study_date
    if last_date is None or study_date > last_date + timedelta(days=1):
        # streak broken or first record
        row.current_streak_days = 1
    elif study_date == last_date:
        # same day, keep streak
        pass
    else:  # study_date == last_date + 1
        row.current_streak_days += 1

    if row.current_streak_days > row.longest_streak_days:
        row.longest_streak_days = row.current_streak_days

    row.last_study_date = study_date
