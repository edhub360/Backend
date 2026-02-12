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


#---------- Quizzes ---------- 
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

# schemas.py (ADD THESE TO YOUR EXISTING FILE)

# ========== FLASHCARD SCHEMAS (Reusing Quiz/Question structure) ==========

class FlashcardItem(BaseModel):
    """Flashcard representation of a quiz question"""
    card_id: str  # Maps to question_id
    front_text: str  # Maps to question_text
    back_text: str  # Maps to correct_answer
    hint: Optional[str] = None  # Maps to explanation
    
    class Config:
        from_attributes = True


class FlashcardDeckListItem(BaseModel):
    """Flashcard deck list (same as QuizListItem)"""
    deck_id: str  # Maps to quiz_id
    title: str
    description: str
    subject_tag: str
    difficulty_level: str
    total_cards: int  # Maps to total_questions
    is_active: bool
    
    class Config:
        from_attributes = True


class FlashcardDeckDetail(BaseModel):
    """Flashcard deck with all cards"""
    deck_id: str  # Maps to quiz_id
    title: str
    description: str
    subject_tag: str
    difficulty_level: str
    cards: List[FlashcardItem] = []
    
    class Config:
        from_attributes = True

class FlashcardAnalyticsCreate(BaseModel):
    deck_id: str
    user_id: str
    card_reviewed: bool = True
    time_taken: float

class FlashcardAnalyticsOut(BaseModel):
    analytics_id: str
    deck_id: str
    user_id: str
    card_reviewed: bool
    time_taken: float
    reviewed_at: datetime

    class Config:
        from_attributes = True

class PaginationMeta(BaseModel):
    total: int
    offset: int
    limit: int
    has_more: bool

class FlashcardDecksResponse(BaseModel):
    decks: List[FlashcardDeckDetail]
    pagination: PaginationMeta