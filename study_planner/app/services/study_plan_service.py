from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.config import get_settings
from app.models.study_plan import StudyPlan
from app.models.study_item import StudyItem
from app.models.user import User
from app.models.courses import Course
from app.schemas.study_plan import (
    StudyPlanCreate, StudyPlanUpdate, StudyPlanRead
)
from app.schemas.study_item import (
    StudyItemCreate, StudyItemUpdate, StudyItemRead
)
from app.schemas.courses import CourseRead
from typing import List
from datetime import datetime

settings = get_settings()
ADMIN_USER_ID = UUID(settings.ADMIN_USER_ID)

## StudyPlan CRUD ##

async def create_study_plan(db: AsyncSession, current_user_id: UUID, data: StudyPlanCreate) -> StudyPlan:
    """Create plan; auto-set is_predefined for admin."""
    is_predefined = (current_user_id == ADMIN_USER_ID)
    plan = StudyPlan(
        user_id=current_user_id,
        is_predefined=is_predefined,
        **data.dict()
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan, attribute_names=["study_items"])
    return plan

async def get_study_plan_by_id(db: AsyncSession, plan_id: UUID) -> StudyPlan | None:
    """Get study plan by ID (no user visibility check)."""
    stmt = (
        select(StudyPlan)
        .options(selectinload(StudyPlan.study_items))
        .where(StudyPlan.id == plan_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()

## NEW: Courses for Dropdown ##
async def list_courses(db: AsyncSession, search: str = "") -> List[CourseRead]:
    """Fetch courses from DB for study plan dropdown. Search title/code/category."""
    stmt = select(Course).order_by(Course.course_title)
    if search:
        stmt = stmt.where(
            or_(
                Course.course_title.ilike(f"%{search}%"),
                Course.course_code.ilike(f"%{search}%"),
                Course.course_category.ilike(f"%{search}%")
            )
        )
    stmt = stmt.limit(100)  # Dropdown perf
    
    result = await db.execute(stmt)
    courses = result.scalars().all()
    return [CourseRead.model_validate(course) for course in courses]  # Pydantic v2


async def create_from_predefined(
    db: AsyncSession, 
    current_user_id: UUID, 
    plan_data: StudyPlanCreate, 
    predefined_plan_id: UUID
) -> StudyPlan:
    """Create user study plan by copying from predefined plan."""
    
    # 1. Fetch predefined plan + its study items
    predefined_plan = await get_study_plan_by_id(db, predefined_plan_id)
    if not predefined_plan or not predefined_plan.is_predefined:
        raise HTTPException(status_code=404, detail="Predefined plan not found")
    
    # 2. Create new user plan (name/description override)
    user_plan = StudyPlan(
        user_id=current_user_id,
        name=plan_data.name,
        description=plan_data.description,
        is_predefined=False  # User's copy is never predefined
    )
    db.add(user_plan)
    await db.commit()
    await db.refresh(user_plan)
    
    # 3. Copy ALL study items from predefined → new plan
    for orig_item in predefined_plan.study_items:
        new_item = StudyItem(
            study_plan_id=user_plan.id,          #  New plan ID
            user_id=current_user_id,             #  Current user
            course_code=orig_item.course_code,
            title=orig_item.title,
            status=orig_item.status,             # 'planned' by default
            position_index=orig_item.position_index,
            term_name=orig_item.term_name,
            course_category=orig_item.course_category,
            course_id=orig_item.course_id,       # null initially
            #duration=orig_item.duration or 0
        )
        db.add(new_item)
    
    await db.commit()
    await db.refresh(user_plan, attribute_names=["study_items"])
    
    return user_plan


async def list_study_plans(db: AsyncSession, current_user_id: UUID) -> List[StudyPlan]:
    """List predefined (admin) + user's plans; predefined first."""
    stmt = (
        select(StudyPlan)
        .where(or_(StudyPlan.is_predefined == True, StudyPlan.user_id == current_user_id))
        .options(selectinload(StudyPlan.study_items))
        .order_by(desc(StudyPlan.is_predefined), desc(StudyPlan.created_at))
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique())

async def get_study_plan_or_404(db: AsyncSession, current_user_id: UUID, plan_id: UUID) -> StudyPlan:
    """Get plan if predefined or owned by user."""
    stmt = (
        select(StudyPlan)
        .options(selectinload(StudyPlan.study_items))
        .where(StudyPlan.id == plan_id)
        .where(or_(StudyPlan.is_predefined == True, StudyPlan.user_id == current_user_id))
    )
    result = await db.execute(stmt)
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Study plan not found")
    return plan

async def update_study_plan(db: AsyncSession, current_user_id: UUID, plan_id: UUID, data: StudyPlanUpdate) -> StudyPlan:
    """Update custom plans only."""
    plan = await get_study_plan_or_404(db, current_user_id, plan_id)
    if plan.is_predefined:
        raise HTTPException(status_code=403, detail="Cannot update predefined plans")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    plan.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(plan)
    return plan

async def delete_study_plan(db: AsyncSession, current_user_id: UUID, plan_id: UUID) -> None:
    """Delete custom plans (cascade deletes items)."""
    plan = await get_study_plan_or_404(db, current_user_id, plan_id)
    if plan.is_predefined:
        raise HTTPException(status_code=403, detail="Cannot delete predefined plans")
    await db.delete(plan)
    await db.commit()

## StudyItem CRUD ##

async def list_study_items(db: AsyncSession, current_user_id: UUID) -> List[StudyItem]:
    """List user's items + items from visible predefined plans."""
    predefined_plans = select(StudyPlan.id).where(or_(StudyPlan.is_predefined == True, StudyPlan.user_id == current_user_id))
    stmt = (
        select(StudyItem)
        .where(or_(StudyItem.user_id == current_user_id, StudyItem.study_plan_id.in_(predefined_plans)))
        .order_by(StudyItem.term_name, StudyItem.position_index)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def create_study_item(db: AsyncSession, current_user_id: UUID, data: StudyItemCreate) -> StudyItem:
    """Create item; validate study_plan_id visibility."""
    if data.study_plan_id:
        await get_study_plan_or_404(db, current_user_id, data.study_plan_id)
    item = StudyItem(
        user_id=current_user_id,
        term_name=data.term_name,
        course_category=data.course_category,
        **data.dict(exclude={"term_name", "course_category"})
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

## Study Items by Plan ##
async def get_study_items_by_plan_id(
    db: AsyncSession, 
    current_user_id: UUID, 
    plan_id: UUID
) -> List[StudyItem]:
    """Get study items filtered by studyplanid foreign key with user visibility check."""
    
    # Verify plan exists and is visible to user
    plan = await get_study_plan_or_404(db, current_user_id, plan_id)
    
    # Get items for this specific plan
    stmt = (
        select(StudyItem)
        .where(StudyItem.study_plan_id == plan_id)
        .order_by(StudyItem.position_index, StudyItem.term_name)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_study_item_or_404(db: AsyncSession, current_user_id: UUID, item_id: UUID) -> StudyItem:
    """Get item if owned or in visible plan."""
    # First check direct ownership
    stmt = select(StudyItem).where(StudyItem.item_id == item_id, StudyItem.user_id == current_user_id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if item:
        return item
    
    # Check via plan
    predefined_plans = select(StudyPlan.id).where(or_(StudyPlan.is_predefined == True, StudyPlan.user_id == current_user_id))
    stmt = select(StudyItem).where(StudyItem.item_id == item_id, StudyItem.study_plan_id.in_(predefined_plans))
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Study item not found")
    return item

async def update_study_item(db: AsyncSession, current_user_id: UUID, item_id: UUID, data: StudyItemUpdate) -> StudyItem:
    """Update item if owned (or via visible plan? restrict to owned)."""
    item = await get_study_item_or_404(db, current_user_id, item_id)
    # For simplicity, only allow update if user_id matches (even for predefined plans)
    if item.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot update items from predefined plans")
    
    update_dict = data.model_dump(exclude_unset=True)
    if "study_plan_id" in update_dict:
        await get_study_plan_or_404(db, current_user_id, update_dict["study_plan_id"])
    for field, value in update_dict.items():
        setattr(item, field, value)
    item.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(item)
    return item

async def delete_study_item(db: AsyncSession, current_user_id: UUID, item_id: UUID) -> None:
    """Delete owned items only."""
    item = await get_study_item_or_404(db, current_user_id, item_id)
    if item.user_id != current_user_id:
        raise HTTPException(status_code=403, detail="Cannot delete items from predefined plans")
    await db.delete(item)
    await db.commit()

## Summary (group by term_name/course_category) ##
async def compute_summary(db: AsyncSession, current_user_id: UUID) -> dict:
    """Summary: courses per term_name."""
    predefined_plans = select(StudyPlan.id).where(or_(StudyPlan.is_predefined == True, StudyPlan.user_id == current_user_id))
    stmt = (
        select(StudyItem.term_name, func.count(StudyItem.course_code).label("course_count"))
        .where(or_(StudyItem.user_id == current_user_id, StudyItem.study_plan_id.in_(predefined_plans)))
        .group_by(StudyItem.term_name)
        .order_by(StudyItem.term_name)
    )
    result = await db.execute(stmt)
    return {"terms": [{"term_name": row.term_name, "course_count": row.course_count} for row in result]}
