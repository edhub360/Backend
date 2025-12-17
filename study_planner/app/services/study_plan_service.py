from typing import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

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

def list_terms(db: Session, user_id: UUID) -> list[Term]:
    stmt = (
        select(Term)
        .where(Term.user_id == user_id, Term.is_archived.is_(False))
        .order_by(Term.position_index)
    )
    return list(db.scalars(stmt).unique())


def create_term(db: Session, user_id: UUID, data: TermCreate) -> Term:
    term = Term(
        user_id=user_id,
        name=data.name,
        start_date=data.start_date,
        end_date=data.end_date,
        position_index=data.position_index,
        is_archived=data.is_archived,
    )
    db.add(term)
    db.commit()
    db.refresh(term)
    return term


def _get_term_or_404(db: Session, user_id: UUID, term_id: UUID) -> Term:
    term = db.get(Term, term_id)
    if not term or term.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")
    return term


def update_term(db: Session, user_id: UUID, term_id: UUID, data: TermUpdate) -> Term:
    term = _get_term_or_404(db, user_id, term_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(term, field, value)
    db.commit()
    db.refresh(term)
    return term


def delete_term(db: Session, user_id: UUID, term_id: UUID) -> None:
    term = _get_term_or_404(db, user_id, term_id)
    db.delete(term)
    db.commit()


# ---------- Requirement Categories ----------

def list_requirements(db: Session, user_id: UUID) -> list[RequirementCategory]:
    stmt = select(RequirementCategory).where(RequirementCategory.user_id == user_id)
    return list(db.scalars(stmt).unique())


def create_requirement(
    db: Session, user_id: UUID, data: RequirementCategoryCreate
) -> RequirementCategory:
    rc = RequirementCategory(
        user_id=user_id,
        name=data.name,
        short_code=data.short_code,
        color=data.color,
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return rc


def _get_requirement_or_404(
    db: Session, user_id: UUID, rc_id: UUID
) -> RequirementCategory:
    rc = db.get(RequirementCategory, rc_id)
    if not rc or rc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Requirement category not found")
    return rc


def update_requirement(
    db: Session, user_id: UUID, rc_id: UUID, data: RequirementCategoryUpdate
) -> RequirementCategory:
    rc = _get_requirement_or_404(db, user_id, rc_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rc, field, value)
    db.commit()
    db.refresh(rc)
    return rc


def delete_requirement(db: Session, user_id: UUID, rc_id: UUID) -> None:
    rc = _get_requirement_or_404(db, user_id, rc_id)
    db.delete(rc)
    db.commit()


# ---------- Study Items ----------

def _get_item_or_404(db: Session, user_id: UUID, item_id: UUID) -> StudyItem:
    item = db.get(StudyItem, item_id)
    if not item or item.user_id != user_id:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def list_items_for_term(db: Session, user_id: UUID, term_id: UUID) -> list[StudyItem]:
    _ = _get_term_or_404(db, user_id, term_id)
    stmt = (
        select(StudyItem)
        .where(StudyItem.user_id == user_id, StudyItem.term_id == term_id)
        .order_by(StudyItem.position_index)
    )
    return list(db.scalars(stmt).unique())


def create_item(
    db: Session, user_id: UUID, data: StudyItemCreate
) -> StudyItem:
    _ = _get_term_or_404(db, user_id, data.term_id)
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
    db.commit()
    db.refresh(item)
    return item


def update_item(
    db: Session, user_id: UUID, item_id: UUID, data: StudyItemUpdate
) -> StudyItem:
    item = _get_item_or_404(db, user_id, item_id)
    payload = data.model_dump(exclude_unset=True)
    if "term_id" in payload:
        _ = _get_term_or_404(db, user_id, payload["term_id"])
    for field, value in payload.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


def delete_item(db: Session, user_id: UUID, item_id: UUID) -> None:
    item = _get_item_or_404(db, user_id, item_id)
    db.delete(item)
    db.commit()


# ---------- Reorder & Summary ----------

def reorder_items(
    db: Session,
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
        _ = _get_term_or_404(db, user_id, term_id)

        stmt = (
            update(StudyItem)
            .where(StudyItem.id == item_id, StudyItem.user_id == user_id)
            .values(term_id=term_id, position_index=pos)
        )
        result = db.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    db.commit()


def compute_summary(db: Session, user_id: UUID) -> PlanSummary:
    stmt = (
        select(
            StudyItem.term_id,
            Term.name,
            func.count(StudyItem.id),
            func.coalesce(func.sum(StudyItem.units), 0),
        )
        .join(Term, Term.id == StudyItem.term_id)
        .where(StudyItem.user_id == user_id)
        .group_by(StudyItem.term_id, Term.name)
        .order_by(Term.position_index)
    )

    per_term = []
    overall_units = 0
    for term_id, term_name, count_items, total_units in db.execute(stmt):
        per_term.append(
            TermSummary(
                term_id=term_id,
                term_name=term_name,
                course_count=count_items,
                total_units=total_units,
            )
        )
        overall_units += total_units

    return PlanSummary(per_term=per_term, overall_total_units=overall_units)
