from pydantic import BaseModel
class CourseRead(BaseModel):
    id: str | None
    code: str
    title: str
    category: str
    duration: int = 3
    # Add image_url, etc.
