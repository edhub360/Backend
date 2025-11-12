# app/utils/moderation.py

HARMFUL_WORDS = {
    "kill", "hate", "rape", "porn", "murder", "terror", "abuse", "drugs",
    "violence", "suicide", "harass", "molest", "gun", "bomb",
    # Add relevant terms/phrases per your policies
}

def contains_harmful_content(text: str) -> bool:
    text_lower = text.lower()
    return any(word in text_lower for word in HARMFUL_WORDS)
