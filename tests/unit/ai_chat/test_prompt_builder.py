import pytest
from app.modules.ai_chat.prompt_builder import build_prompt

def test_prompt_builder_includes_user_message():
    user_msg = "Explain photosynthesis"
    history = []
    prompt = build_prompt(user_msg, history=[])
    assert "Explain gravity" in prompt
    assert "EdHub360" in prompt
    assert "photosynthesis" in prompt
    assert "You are EdHub360 AI Tutor" in prompt
    assert "student-friendly" in prompt
