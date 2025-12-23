from typing import Any, List
from pydantic import BaseModel
from fastapi import APIRouter, status

from app.api.deps import DBSessionDep, CurrentUserDep
from app.schemas.term import TermCreate, TermRead, TermUpdate
from app.schemas.requirement_category import (
    RequirementCategoryCreate,
    RequirementCategoryRead,
    RequirementCategoryUpdate,
)
from app.schemas.study_item import (
    StudyItemCreate,
    StudyItemRead,
    StudyItemUpdate,
)
from app.schemas.summary import PlanSummary
from app.services import study_plan_service as svc

router = APIRouter(prefix="/study-plan", tags=["study-plan"])

# ---------- Terms ----------

@router.get("/terms", response_model=list[TermRead])
async def list_terms(db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.list_terms(db, current_user.id)


@router.post("/terms", response_model=TermRead, status_code=status.HTTP_201_CREATED)
async def create_term(
    data: TermCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.create_term(db, current_user.id, data)


@router.get("/terms/{term_id}", response_model=TermRead)
async def get_term(
    term_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc._get_term_or_404(db, current_user.id, term_id)


@router.patch("/terms/{term_id}", response_model=TermRead)
async def update_term(
    term_id: str,
    data: TermUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.update_term(db, current_user.id, term_id, data)


@router.delete("/terms/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_term(
    term_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    await svc.delete_term(db, current_user.id, term_id)
    return None

# ---------- Requirement Categories ----------

@router.get("/requirements", response_model=list[RequirementCategoryRead])
async def list_requirements(db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.list_requirements(db, current_user.id)


@router.post(
    "/requirements",
    response_model=RequirementCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement(
    data: RequirementCategoryCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.create_requirement(db, current_user.id, data)


@router.patch("/requirements/{rc_id}", response_model=RequirementCategoryRead)
async def update_requirement(
    rc_id: str,
    data: RequirementCategoryUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.update_requirement(db, current_user.id, rc_id, data)


@router.delete("/requirements/{rc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement(
    rc_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    await svc.delete_requirement(db, current_user.id, rc_id)
    return None

# ---------- Study Items ----------

@router.get("/items", response_model=list[StudyItemRead])
async def list_all_items(
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.list_all_items_for_user(db, current_user.id)


@router.get("/terms/{term_id}/items", response_model=list[StudyItemRead])
async def list_items_for_term(
    term_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.list_items_for_term(db, current_user.id, term_id)


@router.post(
    "/items",
    response_model=StudyItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_item(
    data: StudyItemCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.create_item(db, current_user.id, data)


@router.patch("/items/{item_id}", response_model=StudyItemRead)
async def update_item(
    item_id: str,
    data: StudyItemUpdate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.update_item(db, current_user.id, item_id, data)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    await svc.delete_item(db, current_user.id, item_id)
    return None

# ---------- Reorder & Summary ----------

class ReorderItem(BaseModel):
    item_id: str
    term_id: str
    position_index: int


class ReorderPayload(BaseModel):
    items: List[ReorderItem]


@router.post("/items/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_items(
    payload: ReorderPayload,
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    await svc.reorder_items(
        db,
        current_user.id,
        [item.model_dump() for item in payload.items],
    )
    return None


@router.get("/summary", response_model=PlanSummary)
async def get_summary(
    db: DBSessionDep,
    current_user: CurrentUserDep,
):
    return await svc.compute_summary(db, current_user.id)
