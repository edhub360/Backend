# schemas.py
from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, EmailStr

# ---------- Users ----------
class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    language: Optional[str] = None
    subscription_tier: Optional[str] = None
    study_goals: Optional[Dict[str, Any]] = None
    device_info: Optional[Dict[str, Any]] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    language: Optional[str] = None
    subscription_tier: Optional[str] = None
    study_goals: Optional[Dict[str, Any]] = None
    device_info: Optional[Dict[str, Any]] = None

class UserOut(UserBase):
    user_id: str
    created_at: datetime
    class Config:
        from_attributes = True

# ---------- Questions ----------
class QuestionBase(BaseModel):
    user_id: Optional[str] = None
    input_type: Optional[str] = None
    raw_input: Optional[str] = None
    subject_tag: Optional[str] = None
    difficulty: Optional[str] = None

class QuestionCreate(QuestionBase):
    pass

class QuestionOut(QuestionBase):
    question_id: str
    timestamp: datetime
    class Config:
        from_attributes = True

# ---------- Quizzes ----------
class QuizQuestionItem(BaseModel):
    question: str
    options: List[str]
    correct: int
    explanation: Optional[str] = None

class QuizBase(BaseModel):
    user_id: Optional[str] = None
    questions: Optional[List[QuizQuestionItem]] = None
    score: Optional[float] = None
    time_taken: Optional[int] = None

class QuizCreate(QuizBase):
    pass

class QuizOut(QuizBase):
    quiz_id: str
    class Config:
        from_attributes = True


