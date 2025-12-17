from uuid import UUID
from pydantic import BaseModel


class TermSummary(BaseModel):
    term_id: UUID
    term_name: str
    course_count: int
    total_units: int


class PlanSummary(BaseModel):
    per_term: list[TermSummary]
    overall_total_units: int
