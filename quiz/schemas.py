from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, EmailStr

# ---------- Questions ----------
class QuestionBase(BaseModel):
    user_id: Optional[str] = None
    input_type: Optional[str] = None
    raw_input: Optional[str] = None
    subject_tag: Optional[str] = None
    difficulty: Optional[str] = None
    question_text: str
    correct_answer: str
    incorrect_answers: List[str]
    explanation: Optional[str] = None

class QuestionCreate(QuestionBase):
    quiz_id: str

class QuestionOut(QuestionBase):
    question_id: str
    quiz_id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ---------- Quizzes ----------
class QuizBase(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty_level: Optional[str] = None
    subject_tag: Optional[str] = None
    estimated_time: Optional[int] = None
    tags: Optional[List[str]] = None
    quiz_metadata: Optional[Dict[str, Any]] = None

class QuizCreate(QuizBase):
    user_id: str

class QuizOut(QuizBase):
    quiz_id: str
    user_id: str
    created_at: datetime
    questions: Optional[List[QuestionOut]] = None  # Include related questions
    
    class Config:
        from_attributes = True
