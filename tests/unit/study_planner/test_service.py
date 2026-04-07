import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from fastapi import HTTPException
from study_planner.app.services import study_plan_service as svc
from study_planner.app.schemas.study_plan import StudyPlanCreate, StudyPlanUpdate
from study_planner.app.schemas.study_item import StudyItemCreate, StudyItemUpdate
from tests.unit.study_planner.conftest import (
    make_mock_db, make_mock_plan, make_mock_item, make_mock_course, ADMIN_USER_ID
)

USER_ID = uuid4()
PLAN_ID = uuid4()
ITEM_ID = uuid4()
ADMIN_UUID = UUID(ADMIN_USER_ID)


def scalar_result(value):
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def scalars_result(values):
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    r.scalars.return_value.unique.return_value = values
    return r


class TestCreateStudyPlan:
    @pytest.mark.asyncio
    async def test_regular_user(self):
        db = make_mock_db()
        plan = make_mock_plan(user_id=USER_ID, is_predefined=False)
        with patch("study_planner.app.services.study_plan_service.StudyPlan", return_value=plan):
            result = await svc.create_study_plan(db, USER_ID, StudyPlanCreate(name="P"))
        db.add.assert_called_once()
        db.commit.assert_called_once()
        assert result == plan

    @pytest.mark.asyncio
    async def test_admin_is_predefined(self):
        db = make_mock_db()
        plan = make_mock_plan(user_id=ADMIN_UUID, is_predefined=True)
        with patch("study_planner.app.services.study_plan_service.StudyPlan", return_value=plan), \
             patch("study_planner.app.services.study_plan_service.ADMIN_USER_ID", ADMIN_UUID):
            result = await svc.create_study_plan(db, ADMIN_UUID, StudyPlanCreate(name="P"))
        assert result.is_predefined is True


class TestGetStudyPlanById:
    @pytest.mark.asyncio
    async def test_found(self):
        db = make_mock_db()
        plan = make_mock_plan()
        db.execute.return_value = scalar_result(plan)
        assert await svc.get_study_plan_by_id(db, PLAN_ID) == plan

    @pytest.mark.asyncio
    async def test_not_found(self):
        db = make_mock_db()
        db.execute.return_value = scalar_result(None)
        assert await svc.get_study_plan_by_id(db, PLAN_ID) is None


class TestListStudyPlans:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        db = make_mock_db()
        db.execute.return_value = scalars_result([make_mock_plan(), make_mock_plan(is_predefined=True)])
        assert len(await svc.list_study_plans(db, USER_ID)) == 2

    @pytest.mark.asyncio
    async def test_empty(self):
        db = make_mock_db()
        db.execute.return_value = scalars_result([])
        assert await svc.list_study_plans(db, USER_ID) == []


class TestGetStudyPlanOr404:
    @pytest.mark.asyncio
    async def test_visible_plan(self):
        db = make_mock_db()
        plan = make_mock_plan(user_id=USER_ID)
        db.execute.return_value = scalar_result(plan)
        assert await svc.get_study_plan_or_404(db, USER_ID, PLAN_ID) == plan

    @pytest.mark.asyncio
    async def test_raises_404(self):
        db = make_mock_db()
        db.execute.return_value = scalar_result(None)
        with pytest.raises(HTTPException) as exc:
            await svc.get_study_plan_or_404(db, USER_ID, PLAN_ID)
        assert exc.value.status_code == 404


class TestUpdateStudyPlan:
    @pytest.mark.asyncio
    async def test_updates(self):
        db = make_mock_db()
        plan = make_mock_plan(user_id=USER_ID, is_predefined=False)
        db.execute.return_value = scalar_result(plan)
        result = await svc.update_study_plan(db, USER_ID, PLAN_ID, StudyPlanUpdate(name="U"))
        db.commit.assert_called_once()
        assert result == plan

    @pytest.mark.asyncio
    async def test_predefined_403(self):
        db = make_mock_db()
        plan = make_mock_plan(is_predefined=True)
        db.execute.return_value = scalar_result(plan)
        with pytest.raises(HTTPException) as exc:
            await svc.update_study_plan(db, USER_ID, PLAN_ID, StudyPlanUpdate(name="H"))
        assert exc.value.status_code == 403


class TestDeleteStudyPlan:
    @pytest.mark.asyncio
    async def test_deletes(self):
        db = make_mock_db()
        plan = make_mock_plan(user_id=USER_ID, is_predefined=False)
        db.execute.return_value = scalar_result(plan)
        await svc.delete_study_plan(db, USER_ID, PLAN_ID)
        db.delete.assert_called_once_with(plan)
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_predefined_403(self):
        db = make_mock_db()
        plan = make_mock_plan(is_predefined=True)
        db.execute.return_value = scalar_result(plan)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_study_plan(db, USER_ID, PLAN_ID)
        assert exc.value.status_code == 403


class TestCreateFromPredefined:
    @pytest.mark.asyncio
    async def test_copies_items(self):
        db = make_mock_db()
        item = make_mock_item()
        predefined = make_mock_plan(is_predefined=True, study_items=[item])
        user_plan = make_mock_plan(is_predefined=False)

        with patch("study_planner.app.services.study_plan_service.get_study_plan_by_id",
                   new=AsyncMock(return_value=predefined)), \
             patch("study_planner.app.services.study_plan_service.StudyPlan",
                   return_value=user_plan), \
             patch("study_planner.app.services.study_plan_service.StudyItem",
                   return_value=item):
            await svc.create_from_predefined(db, USER_ID, StudyPlanCreate(name="Copy"), PLAN_ID)

        db.add.assert_called()

    @pytest.mark.asyncio
    async def test_404_not_found(self):
        db = make_mock_db()
        with patch("study_planner.app.services.study_plan_service.get_study_plan_by_id",
                   new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await svc.create_from_predefined(db, USER_ID, StudyPlanCreate(name="Copy"), PLAN_ID)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_404_not_predefined(self):
        db = make_mock_db()
        with patch("study_planner.app.services.study_plan_service.get_study_plan_by_id",
                   new=AsyncMock(return_value=make_mock_plan(is_predefined=False))):
            with pytest.raises(HTTPException) as exc:
                await svc.create_from_predefined(db, USER_ID, StudyPlanCreate(name="Copy"), PLAN_ID)
        assert exc.value.status_code == 404

class TestListStudyItems:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        db = make_mock_db()
        db.execute.return_value = scalars_result([make_mock_item(), make_mock_item()])
        assert len(await svc.list_study_items(db, USER_ID)) == 2

    @pytest.mark.asyncio
    async def test_empty(self):
        db = make_mock_db()
        db.execute.return_value = scalars_result([])
        assert await svc.list_study_items(db, USER_ID) == []


class TestCreateStudyItem:
    @pytest.mark.asyncio
    async def test_creates_without_plan(self):
        db = make_mock_db()
        item = make_mock_item()
        with patch("study_planner.app.services.study_plan_service.StudyItem", return_value=item):
            result = await svc.create_study_item(db, USER_ID, StudyItemCreate(course_code="CS101", title="T"))
        db.add.assert_called_once()
        assert result == item

    @pytest.mark.asyncio
    async def test_validates_plan_id_404(self):
        db = make_mock_db()
        db.execute.return_value = scalar_result(None)
        with pytest.raises(HTTPException) as exc:
            await svc.create_study_item(db, USER_ID,
                StudyItemCreate(course_code="CS101", title="T", study_plan_id=uuid4()))
        assert exc.value.status_code == 404


class TestGetStudyItemOr404:
    @pytest.mark.asyncio
    async def test_owned_item(self):
        db = make_mock_db()
        item = make_mock_item(user_id=USER_ID)
        db.execute.return_value = scalar_result(item)
        assert await svc.get_study_item_or_404(db, USER_ID, ITEM_ID) == item

    @pytest.mark.asyncio
    async def test_raises_404(self):
        db = make_mock_db()
        db.execute.return_value = scalar_result(None)
        with pytest.raises(HTTPException) as exc:
            await svc.get_study_item_or_404(db, USER_ID, ITEM_ID)
        assert exc.value.status_code == 404


class TestUpdateStudyItem:
    @pytest.mark.asyncio
    async def test_owned_update(self):
        db = make_mock_db()
        item = make_mock_item(user_id=USER_ID)
        db.execute.return_value = scalar_result(item)
        result = await svc.update_study_item(db, USER_ID, ITEM_ID, StudyItemUpdate(title="New"))
        db.commit.assert_called_once()
        assert result == item

    @pytest.mark.asyncio
    async def test_other_user_403(self):
        db = make_mock_db()
        item = make_mock_item(user_id=uuid4())
        db.execute.return_value = scalar_result(item)
        with pytest.raises(HTTPException) as exc:
            await svc.update_study_item(db, USER_ID, ITEM_ID, StudyItemUpdate(title="H"))
        assert exc.value.status_code == 403


class TestDeleteStudyItem:
    @pytest.mark.asyncio
    async def test_owned_delete(self):
        db = make_mock_db()
        item = make_mock_item(user_id=USER_ID)
        db.execute.return_value = scalar_result(item)
        await svc.delete_study_item(db, USER_ID, ITEM_ID)
        db.delete.assert_called_once_with(item)

    @pytest.mark.asyncio
    async def test_other_user_403(self):
        db = make_mock_db()
        item = make_mock_item(user_id=uuid4())
        db.execute.return_value = scalar_result(item)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_study_item(db, USER_ID, ITEM_ID)
        assert exc.value.status_code == 403


class TestGetStudyItemsByPlanId:
    @pytest.mark.asyncio
    async def test_returns_items(self):
        db = make_mock_db()
        plan = make_mock_plan()
        items = [make_mock_item(), make_mock_item()]
        call_count = 0

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return scalar_result(plan)
            return scalars_result(items)

        db.execute.side_effect = side_effect
        result = await svc.get_study_items_by_plan_id(db, USER_ID, PLAN_ID)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_plan_not_visible_404(self):
        db = make_mock_db()
        db.execute.return_value = scalar_result(None)
        with pytest.raises(HTTPException) as exc:
            await svc.get_study_items_by_plan_id(db, USER_ID, uuid4())
        assert exc.value.status_code == 404


class TestListCourses:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        db = make_mock_db()
        course = make_mock_course()
        r = MagicMock()
        r.scalars.return_value.all.return_value = [course]
        db.execute.return_value = r
        result = await svc.list_courses(db, "")
        assert len(result) == 1
        assert result[0]["course_code"] == "CS101"

    @pytest.mark.asyncio
    async def test_empty(self):
        db = make_mock_db()
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        db.execute.return_value = r
        assert await svc.list_courses(db, "xyz") == []

    @pytest.mark.asyncio
    async def test_executes_with_search(self):
        db = make_mock_db()
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        db.execute.return_value = r
        await svc.list_courses(db, "python")
        db.execute.assert_called_once()


class TestComputeSummary:
    @pytest.mark.asyncio
    async def test_returns_terms(self):
        db = make_mock_db()
        row = MagicMock()
        row.term_name = "Term 1"
        row.course_count = 3
        r = MagicMock()
        r.__iter__ = MagicMock(return_value=iter([row]))
        db.execute.return_value = r
        result = await svc.compute_summary(db, USER_ID)
        assert result["terms"][0]["term_name"] == "Term 1"
        assert result["terms"][0]["course_count"] == 3

    @pytest.mark.asyncio
    async def test_empty(self):
        db = make_mock_db()
        r = MagicMock()
        r.__iter__ = MagicMock(return_value=iter([]))
        db.execute.return_value = r
        assert (await svc.compute_summary(db, USER_ID))["terms"] == []