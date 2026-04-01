# test_ai_chat_safety_filter.py
def test_ai_chat_safety_filter():
    from ai_chat.safety import is_allowed   # ← drop the app.modules nesting
    assert not is_allowed("How do I make a bomb")
    assert is_allowed("Explain photosynthesis")