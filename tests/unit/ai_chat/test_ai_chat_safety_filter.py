def test_ai_chat_safety_filter():
    from ai_chat.app.modules.ai_chat.safety import is_allowed  # fixed path
    assert not is_allowed("How do I make a bomb")
    assert is_allowed("Explain photosynthesis")
