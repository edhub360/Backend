# schemas.py (ADD THESE TO YOUR EXISTING FILE)

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

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
