import pytest
import sys
from unittest.mock import MagicMock


# Mock app.* submodules to prevent import errors
sys.modules["app"] = MagicMock()
sys.modules["app.config"] = MagicMock()
sys.modules["app.utils"] = MagicMock()

# Import directly from the correct path (no 'modules' folder exists)
from ai_chat.app.utils.prompt_builder import build_prompt

@pytest.mark.unit
def test_prompt_builder_includes_user_message():
    prompt = build_prompt("Explain photosynthesis", history=[])
    assert "Explain photosynthesis" in prompt

@pytest.mark.unit
def test_prompt_builder_includes_system_identity():
    prompt = build_prompt("test", history=[])
    assert "EdHub360" in prompt
    assert "You are EdHub360 AI Tutor" in prompt

@pytest.mark.unit
def test_prompt_builder_includes_student_friendly():
    prompt = build_prompt("test", history=[])
    assert "student-friendly" in prompt

@pytest.mark.unit
def test_prompt_builder_with_history():
    history = [
        {"role": "user", "content": "What is DNA?"},
        {"role": "assistant", "content": "DNA is deoxyribonucleic acid."},
    ]
    prompt = build_prompt("Tell me more", history=history)
    assert "Tell me more" in prompt
