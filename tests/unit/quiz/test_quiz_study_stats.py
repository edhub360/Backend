import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date, timedelta


def make_mock_db(existing_row=None):
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_row

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db


@pytest.mark.unit
class TestUpdateUserStudyStats:

    @pytest.mark.asyncio
    async def test_creates_new_row_for_new_user(self):
        from quiz.study_stats import update_user_study_stats
        today = date.today()
        mock_db = make_mock_db(existing_row=None)

        await update_user_study_stats(mock_db, "user-123", 300, today)

        mock_db.add.assert_called_once()
        added = mock_db.add.call_args[0][0]
        assert added.user_id == "user-123"
        assert added.total_study_seconds == 300
        assert added.current_streak_days == 1
        assert added.longest_streak_days == 1
        assert added.last_study_date == today
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_increments_total_study_seconds(self):
        from quiz.study_stats import update_user_study_stats
        from quiz.models import UserStudyStats
        today = date.today()
        existing = UserStudyStats(
            user_id="user-123",
            total_study_seconds=1000,
            current_streak_days=3,
            longest_streak_days=5,
            last_study_date=today - timedelta(days=1),
        )
        mock_db = make_mock_db(existing_row=existing)

        await update_user_study_stats(mock_db, "user-123", 200, today)

        assert existing.total_study_seconds == 1200
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_streak_increments_on_consecutive_day(self):
        from quiz.study_stats import update_user_study_stats
        from quiz.models import UserStudyStats
        today = date.today()
        yesterday = today - timedelta(days=1)
        existing = UserStudyStats(
            user_id="user-123",
            total_study_seconds=500,
            current_streak_days=3,
            longest_streak_days=3,
            last_study_date=yesterday,
        )
        mock_db = make_mock_db(existing_row=existing)

        await update_user_study_stats(mock_db, "user-123", 100, today)

        assert existing.current_streak_days == 4
        assert existing.longest_streak_days == 4
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_streak_resets_after_missed_day(self):
        from quiz.study_stats import update_user_study_stats
        from quiz.models import UserStudyStats
        today = date.today()
        three_days_ago = today - timedelta(days=3)
        existing = UserStudyStats(
            user_id="user-123",
            total_study_seconds=500,
            current_streak_days=7,
            longest_streak_days=10,
            last_study_date=three_days_ago,
        )
        mock_db = make_mock_db(existing_row=existing)

        await update_user_study_stats(mock_db, "user-123", 100, today)

        assert existing.current_streak_days == 1
        assert existing.longest_streak_days == 10  # unchanged
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_same_day_keeps_streak_unchanged(self):
        from quiz.study_stats import update_user_study_stats
        from quiz.models import UserStudyStats
        today = date.today()
        existing = UserStudyStats(
            user_id="user-123",
            total_study_seconds=300,
            current_streak_days=5,
            longest_streak_days=5,
            last_study_date=today,
        )
        mock_db = make_mock_db(existing_row=existing)

        await update_user_study_stats(mock_db, "user-123", 100, today)

        assert existing.current_streak_days == 5
        assert existing.total_study_seconds == 400
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_longest_streak_updates_when_exceeded(self):
        from quiz.study_stats import update_user_study_stats
        from quiz.models import UserStudyStats
        today = date.today()
        yesterday = today - timedelta(days=1)
        existing = UserStudyStats(
            user_id="user-123",
            total_study_seconds=200,
            current_streak_days=9,
            longest_streak_days=9,
            last_study_date=yesterday,
        )
        mock_db = make_mock_db(existing_row=existing)

        await update_user_study_stats(mock_db, "user-123", 100, today)

        assert existing.current_streak_days == 10
        assert existing.longest_streak_days == 10
        mock_db.commit.assert_awaited_once()
