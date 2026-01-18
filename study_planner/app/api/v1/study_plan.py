from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status, HTTPException, Query
from app.api.deps import DBSessionDep, CurrentUserDep
from app.schemas.study_plan import (
    StudyPlanCreate, StudyPlanRead, StudyPlanUpdate
)
from app.schemas.study_item import (
    StudyItemCreate, StudyItemRead, StudyItemUpdate
)
from app.schemas.courses import CourseRead
from app.services import study_plan_service as svc

router = APIRouter(prefix="/study-plan", tags=["study-plan"])

## Study Plans ##
@router.post("/", response_model=StudyPlanRead, status_code=status.HTTP_201_CREATED)
async def create_plan(data: StudyPlanCreate, db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.create_study_plan(db, current_user.id, data)

## Add this NEW endpoint (after create_plan):
@router.post("/{plan_id}/from-predefined", response_model=StudyPlanRead, status_code=status.HTTP_201_CREATED)
async def create_from_predefined_plan(
    plan_id: str,
    data: StudyPlanCreate,  # Only name + description needed
    db: DBSessionDep, 
    current_user: CurrentUserDep
):
    """Copy predefined study plan → create user copy with custom name/desc."""
    return await svc.create_from_predefined(
        db, current_user.id, data, UUID(plan_id)
    )

@router.get("/", response_model=List[StudyPlanRead])
async def list_plans(db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.list_study_plans(db, current_user.id)

@router.get("/{plan_id}", response_model=StudyPlanRead)
async def get_plan(plan_id: str, db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.get_study_plan_or_404(db, current_user.id, UUID(plan_id))

@router.patch("/{plan_id}", response_model=StudyPlanRead)
async def update_plan(plan_id: str, data: StudyPlanUpdate, db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.update_study_plan(db, current_user.id, UUID(plan_id), data)

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(plan_id: str, db: DBSessionDep, current_user: CurrentUserDep):
    await svc.delete_study_plan(db, current_user.id, UUID(plan_id))

## NEW: Courses Dropdown Endpoint (public-ish, user auth optional) ##
@router.get("/courses", response_model=List[CourseRead])
async def list_courses(
    db: DBSessionDep,
    q: str = Query(None, description="Search title/code"),
    current_user: CurrentUserDep = Depends(CurrentUserDep(required=False))  # Optional auth
):
    """Fetch courses for dropdown in study plan UI."""
    return await svc.list_courses(db, q or "")

## Study Items (flat) ##
@router.post("/items", response_model=StudyItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(data: StudyItemCreate, db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.create_study_item(db, current_user.id, data)

@router.get("/items", response_model=List[StudyItemRead])
async def list_items(db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.list_study_items(db, current_user.id)

@router.get("/items/{item_id}", response_model=StudyItemRead)
async def get_item(item_id: str, db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.get_study_item_or_404(db, current_user.id, UUID(item_id))

@router.patch("/items/{item_id}", response_model=StudyItemRead)
async def update_item(item_id: str, data: StudyItemUpdate, db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.update_study_item(db, current_user.id, UUID(item_id), data)

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: str, db: DBSessionDep, current_user: CurrentUserDep):
    await svc.delete_study_item(db, current_user.id, UUID(item_id))

## Study Items by Plan ##
@router.get("/{plan_id}/items", response_model=List[StudyItemRead])
async def get_items_by_plan(
    plan_id: str, 
    db: DBSessionDep, 
    current_user: CurrentUserDep
):
    """Get all study items for a specific study plan"""
    return await svc.get_study_items_by_plan_id(db, current_user.id, UUID(plan_id))


## Summary ##
@router.get("/summary", response_model=dict)
async def get_summary(db: DBSessionDep, current_user: CurrentUserDep):
    return await svc.compute_summary(db, current_user.id)
