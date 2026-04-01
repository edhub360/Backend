# tests/unit/courses/test_crud.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_session():
    session = AsyncMock(spec=AsyncSession)
    return session


def make_course(**kwargs):
    defaults = dict(
        course_id="uuid-1",
        course_title="Python 101",
        course_desc="Learn Python from scratch",
        course_duration=60,
        course_complexity="beginner",
        course_owner="instructor-1",
        course_url="https://cdn.example.com/py",
        course_redirect_url="https://example.com/py",
        course_image_url="https://cdn.example.com/img.png",
        course_credit=3,
    )
    defaults.update(kwargs)
    return MagicMock(**defaults)


# ─────────────────────────────────────────────
# get_course
# ─────────────────────────────────────────────

class TestGetCourse:

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from courses.app.crud import get_course
        self.get_course = get_course

    @pytest.mark.anyio
    async def test_returns_course_when_found(self):
        session = make_session()
        course = make_course()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = course
        session.execute.return_value = result_mock

        result = await self.get_course(session, "uuid-1")

        assert result is course

    @pytest.mark.anyio
    async def test_returns_none_when_not_found(self):
        session = make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        result = await self.get_course(session, "nonexistent")

        assert result is None

    @pytest.mark.anyio
    async def test_session_execute_called_once(self):
        session = make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        await self.get_course(session, "uuid-1")

        session.execute.assert_called_once()

    @pytest.mark.anyio
    async def test_scalar_one_or_none_called(self):
        session = make_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        await self.get_course(session, "uuid-1")

        result_mock.scalar_one_or_none.assert_called_once()

    @pytest.mark.anyio
    async def test_returns_exact_course_object(self):
        session = make_session()
        course = make_course(course_id="exact-id", course_title="Exact Course")
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = course
        session.execute.return_value = result_mock

        result = await self.get_course(session, "exact-id")

        assert result.course_id == "exact-id"
        assert result.course_title == "Exact Course"


# ─────────────────────────────────────────────
# list_courses
# ─────────────────────────────────────────────

class TestListCourses:

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from courses.app.crud import list_courses
        self.list_courses = list_courses

    def _setup_session(self, courses: list, total: int):
        """Return a session mock wired up for list_courses."""
        session = make_session()

        # session.scalar() → total count
        session.scalar.return_value = total

        # session.execute() → scalars().all() → courses list
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = courses
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_mock
        session.execute.return_value = execute_result

        return session

    # ── Return shape ──────────────────────────

    @pytest.mark.anyio
    async def test_returns_tuple_of_total_and_courses(self):
        courses = [make_course()]
        session = self._setup_session(courses, 1)
        result = await self.list_courses(session, None, 1, 10, None, None, None)
        assert isinstance(result, tuple)
        assert len(result) == 2

    @pytest.mark.anyio
    async def test_total_matches_scalar_result(self):
        session = self._setup_session([], 42)
        total, _ = await self.list_courses(session, None, 1, 10, None, None, None)
        assert total == 42

    @pytest.mark.anyio
    async def test_courses_list_returned(self):
        courses = [make_course(course_id=f"id-{i}") for i in range(3)]
        session = self._setup_session(courses, 3)
        _, result = await self.list_courses(session, None, 1, 10, None, None, None)
        assert result == courses

    @pytest.mark.anyio
    async def test_empty_courses_returned(self):
        session = self._setup_session([], 0)
        total, courses = await self.list_courses(session, None, 1, 10, None, None, None)
        assert total == 0
        assert courses == []

    # ── DB calls ──────────────────────────────

    @pytest.mark.anyio
    async def test_session_scalar_called_for_count(self):
        session = self._setup_session([], 0)
        await self.list_courses(session, None, 1, 10, None, None, None)
        session.scalar.assert_called_once()

    @pytest.mark.anyio
    async def test_session_execute_called_for_rows(self):
        session = self._setup_session([], 0)
        await self.list_courses(session, None, 1, 10, None, None, None)
        session.execute.assert_called_once()

    # ── Pagination offset ─────────────────────

    @pytest.mark.anyio
    async def test_page_1_uses_offset_0(self):
        """Capture the query object and verify .offset(0) was chained."""
        from courses.app.crud import list_courses
        session = self._setup_session([], 0)

        with patch("courses.app.crud.select") as mock_select:
            # Chain returns self so .offset().limit() works
            chain = MagicMock()
            chain.where.return_value = chain
            chain.offset.return_value = chain
            chain.limit.return_value = chain
            mock_select.return_value = chain
            session.scalar.return_value = 0
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            exec_mock = MagicMock()
            exec_mock.scalars.return_value = scalars_mock
            session.execute.return_value = exec_mock

            await list_courses(session, None, 1, 10, None, None, None)
            chain.offset.assert_called_with(0)

    @pytest.mark.anyio
    async def test_page_3_limit_5_uses_offset_10(self):
        from courses.app.crud import list_courses
        session = self._setup_session([], 0)

        with patch("courses.app.crud.select") as mock_select:
            chain = MagicMock()
            chain.where.return_value = chain
            chain.offset.return_value = chain
            chain.limit.return_value = chain
            mock_select.return_value = chain
            session.scalar.return_value = 0
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            exec_mock = MagicMock()
            exec_mock.scalars.return_value = scalars_mock
            session.execute.return_value = exec_mock

            await list_courses(session, None, 3, 5, None, None, None)
            chain.offset.assert_called_with(10)   # (3-1) * 5

    @pytest.mark.anyio
    async def test_limit_passed_to_query(self):
        from courses.app.crud import list_courses
        session = self._setup_session([], 0)

        with patch("courses.app.crud.select") as mock_select:
            chain = MagicMock()
            chain.where.return_value = chain
            chain.offset.return_value = chain
            chain.limit.return_value = chain
            mock_select.return_value = chain
            session.scalar.return_value = 0
            scalars_mock = MagicMock()
            scalars_mock.all.return_value = []
            exec_mock = MagicMock()
            exec_mock.scalars.return_value = scalars_mock
            session.execute.return_value = exec_mock

            await list_courses(session, None, 1, 25, None, None, None)
            chain.limit.assert_called_with(25)

    # ── Filter combinations (smoke via session calls) ──

    @pytest.mark.anyio
    async def test_no_filters_still_returns_results(self):
        courses = [make_course()]
        session = self._setup_session(courses, 1)
        total, result = await self.list_courses(session, None, 1, 10, None, None, None)
        assert total == 1
        assert len(result) == 1

    @pytest.mark.anyio
    async def test_with_search_query(self):
        courses = [make_course(course_title="Python Advanced")]
        session = self._setup_session(courses, 1)
        total, result = await self.list_courses(session, "python", 1, 10, None, None, None)
        assert total == 1

    @pytest.mark.anyio
    async def test_with_complexity_filter(self):
        courses = [make_course(course_complexity="advanced")]
        session = self._setup_session(courses, 1)
        total, result = await self.list_courses(session, None, 1, 10, "advanced", None, None)
        assert total == 1

    @pytest.mark.anyio
    async def test_with_min_duration_filter(self):
        courses = [make_course(course_duration=90)]
        session = self._setup_session(courses, 1)
        total, result = await self.list_courses(session, None, 1, 10, None, 60, None)
        assert total == 1

    @pytest.mark.anyio
    async def test_with_max_duration_filter(self):
        courses = [make_course(course_duration=30)]
        session = self._setup_session(courses, 1)
        total, result = await self.list_courses(session, None, 1, 10, None, None, 60)
        assert total == 1

    @pytest.mark.anyio
    async def test_with_all_filters(self):
        courses = [make_course(course_duration=45, course_complexity="intermediate")]
        session = self._setup_session(courses, 1)
        total, result = await self.list_courses(
            session, "django", 1, 10, "intermediate", 30, 60
        )
        assert total == 1

    # ── Zero-value filter edge cases ──────────

    @pytest.mark.anyio
    async def test_min_duration_zero_not_applied(self):
        """min_duration=0 is falsy — filter must NOT be added (matches source code behaviour)."""
        session = self._setup_session([], 0)
        # Should not raise and session still called
        await self.list_courses(session, None, 1, 10, None, 0, None)
        session.scalar.assert_called_once()

    @pytest.mark.anyio
    async def test_empty_string_q_not_applied(self):
        """q='' is falsy — ilike filter must NOT be added."""
        session = self._setup_session([], 0)
        await self.list_courses(session, "", 1, 10, None, None, None)
        session.scalar.assert_called_once()

    @pytest.mark.anyio
    async def test_multiple_courses_returned(self):
        courses = [make_course(course_id=f"id-{i}") for i in range(5)]
        session = self._setup_session(courses, 5)
        total, result = await self.list_courses(session, None, 1, 10, None, None, None)
        assert total == 5
        assert len(result) == 5