from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.term import Term
from app.models.study_item import StudyItem
from app.models.requirement_category import RequirementCategory
from app.schemas.term import TermCreate, TermUpdate
from app.schemas.study_item import StudyItemCreate, StudyItemUpdate
from app.schemas.requirement_category import (
    RequirementCategoryCreate,
    RequirementCategoryUpdate,
)
from app.schemas.summary import PlanSummary, TermSummary


# ---------- Terms ----------

async def list_terms(db: AsyncSession, user_id: UUID) -> list[Term]:
    stmt = (
        select(Term)
        .options(selectinload(Term.study_items))
        .where(Term.user_id == user_id, Term.is_archived.is_(False))
        .order_by(Term.position_index)
    )
    result = await db.scalars(stmt)
    return list(result.unique())


async def create_item(db: AsyncSession, user_id: UUID, data: StudyItemCreate) -> StudyItem:
    item = StudyItem(
        user_id=user_id,
        term_id=data.term_id,
        requirement_category_id=data.requirement_category_id,
        course_code=data.course_code,
        title=data.title,
        units=data.units,
        status=data.status,
        position_index=data.position_index,
        notes=data.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    result = await db.scalars(
        select(StudyItem)
        .options(selectinload(StudyItem.requirement_category))
        .where(StudyItem.id == item.id)
    )
    return result.one()



async def _get_term_or_404(db: AsyncSession, user_id: UUID, term_id: UUID) -> Term:
    stmt = (
        select(Term)
        .options(selectinload(Term.study_items))
        .where(Term.id == term_id, Term.user_id == user_id)
    )
    result = await db.scalars(stmt)
    term = result.first()
    if not term:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")
    return term


async def update_term(
    db: AsyncSession, user_id: UUID, term_id: UUID, data: TermUpdate
) -> Term:
    term = await _get_term_or_404(db, user_id, term_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(term, field, value)
    await db.commit()
    await db.refresh(term)
    return term


async def delete_term(db: AsyncSession, user_id: UUID, term_id: UUID) -> None:
    term = await _get_term_or_404(db, user_id, term_id)
    await db.delete(term)
    await db.commit()


# ---------- Requirement Categories ----------

async def list_requirements(
    db: AsyncSession, user_id: UUID
) -> list[RequirementCategory]:
    stmt = select(RequirementCategory).where(RequirementCategory.user_id == user_id)
    result = await db.scalars(stmt)
    return list(result.unique())


async def create_requirement(
    db: AsyncSession, user_id: UUID, data: RequirementCategoryCreate
) -> RequirementCategory:
    rc = RequirementCategory(
        user_id=user_id,
        name=data.name,
        short_code=data.short_code,
        color=data.color,
    )
    db.add(rc)
    await db.commit()
    await db.refresh(rc)
    return rc


async def _get_requirement_or_404(
    db: AsyncSession, user_id: UUID, rc_id: UUID
) -> RequirementCategory:
    rc = await db.get(RequirementCategory, rc_id)
    if not rc or rc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Requirement category not found")
    return rc


async def update_requirement(
    db: AsyncSession, user_id: UUID, rc_id: UUID, data: RequirementCategoryUpdate
) -> RequirementCategory:
    rc = await _get_requirement_or_404(db, user_id, rc_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rc, field, value)
    await db.commit()
    await db.refresh(rc)
    return rc


async def delete_requirement(db: AsyncSession, user_id: UUID, rc_id: UUID) -> None:
    rc = await _get_requirement_or_404(db, user_id, rc_id)
    await db.delete(rc)
    await db.commit()


# ---------- Study Items ----------

# study_plan_service.py - list_all_items_for_user
async def list_all_items_for_user(db: AsyncSession, user_id: UUID) -> list[StudyItem]:
    stmt = (
        select(StudyItem)
        .where(StudyItem.user_id == user_id)  # ✅ FIXED
        .order_by(StudyItem.term_name, StudyItem.position_index)
    )
    result = await db.scalars(stmt)
    return result.all()

# _get_item_or_404
async def _get_item_or_404(db: AsyncSession, user_id: UUID, item_id: UUID) -> StudyItem:
    item = await db.get(StudyItem, item_id)
    if not item or item.user_id != user_id:  # ✅ FIXED
        raise HTTPException(status_code=404, detail="Item not found")
    return item



async def list_items_for_term(
    db: AsyncSession, user_id: UUID, term_id: UUID
) -> list[StudyItem]:
    _ = await _get_term_or_404(db, user_id, term_id)
    stmt = (
        select(StudyItem)
        .where(StudyItem.user_id == user_id, StudyItem.term_id == term_id)
        .order_by(StudyItem.position_index)
    )
    result = await db.scalars(stmt)
    return list(result.unique())


async def create_item(db: AsyncSession, user_id: UUID, data: StudyItemCreate) -> StudyItem:
    # Validate term (ID OR name)
    if data.term_id:
        await _get_term_or_404(db, user_id, data.term_id)
        term_name = None  # Will auto-populate from DB
    elif data.term_name:
        term = await db.scalar(select(Term).where(Term.user_id == user_id, Term.name == data.term_name))
        if not term:
            raise HTTPException(404, f"Term '{data.term_name}' not found")
        term_name = data.term_name
    else:
        raise HTTPException(400, "term_id or term_name required")
    
    item = StudyItem(
        user_id=user_id,
        term_id=data.term_id,  # Keep FK
        term_name=term_name,   # ✅ NEW
        requirement_category_id=data.requirement_category_id,
        requirement_category_name=data.requirement_category_name,  # ✅ NEW
        course_code=data.course_code,
        title=data.title,
        units=data.units,
        status=data.status,
        position_index=data.position_index,
        notes=data.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(db: AsyncSession, user_id: UUID, item_id: UUID, data: StudyItemUpdate) -> StudyItem:
    item = await _get_item_or_404(db, user_id, item_id)
    payload = data.model_dump(exclude_unset=True)
    
    # Validate term change
    if "term_id" in payload:
        await _get_term_or_404(db, user_id, payload["term_id"])
    if "term_name" in payload:
        term = await db.scalar(select(Term).where(Term.user_id == user_id, Term.name == payload["term_name"]))
        if not term:
            raise HTTPException(404, f"Term '{payload['term_name']}' not found")
    
    for field, value in payload.items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, user_id: UUID, item_id: UUID) -> None:
    item = await _get_item_or_404(db, user_id, item_id)
    await db.delete(item)
    await db.commit()


# ---------- Reorder & Summary ----------

async def reorder_items(
    db: AsyncSession,
    user_id: UUID,
    items: list[dict],
) -> None:
    """
    items: [{ "item_id": UUID, "term_id": UUID, "position_index": int }, ...]
    """
    for payload in items:
        item_id = payload["item_id"]
        term_id = payload["term_id"]
        pos = payload["position_index"]

        # Validate term belongs to user
        _ = await _get_term_or_404(db, user_id, term_id)

        stmt = (
            update(StudyItem)
            .where(StudyItem.id == item_id, StudyItem.user_id == user_id)
            .values(term_id=term_id, position_index=pos)
        )
        result = await db.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    await db.commit()


async def compute_summary(db: AsyncSession, user_id: UUID) -> PlanSummary:
    """No JOIN - uses denormalized term_name"""
    stmt = (
        select(
            StudyItem.term_name,  # ✅ Direct column
            func.count(StudyItem.id),
            func.coalesce(func.sum(StudyItem.units), 0),
        )
        .where(StudyItem.user_id == user_id)
        .group_by(StudyItem.term_name)
        .order_by(StudyItem.term_name)  # ✅ Alphabetical
    )
    result = await db.execute(stmt)
    
    per_term: list[TermSummary] = []
    overall_units = 0
    for term_name, count_items, total_units in result:
        per_term.append(
            TermSummary(
                term_id=None,  # Not needed
                term_name=term_name,
                course_count=count_items,
                total_units=total_units,
            )
        )
        overall_units += total_units
    
    return PlanSummary(per_term=per_term, overall_total_units=overall_units)

