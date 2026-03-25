import pytest
import sys
from unittest.mock import MagicMock

sys.modules.setdefault("app", MagicMock())
sys.modules.setdefault("app.modules", MagicMock())
sys.modules.setdefault("app.modules.ai_chat", MagicMock())
sys.modules.setdefault("app.modules.ai_chat.prompt_builder", MagicMock())

# Then your actual import
from ai_chat.app.modules.ai_chat.prompt_builder import build_prompt

def test_prompt_builder_includes_user_message():
    user_msg = "Explain photosynthesis"
    history = []
    prompt = build_prompt(user_msg, history=[])
    assert "Explain photosynthesis" in prompt
    assert "EdHub360" in prompt
    assert "photosynthesis" in prompt
    assert "You are EdHub360 AI Tutor" in prompt
    assert "student-friendly" in prompt
