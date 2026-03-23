from app.modules.ai_chat.prompt_builder import build_prompt

def test_prompt_builder_includes_user_message():
    prompt = build_prompt("Explain gravity", history=[])
    assert "Explain gravity" in prompt
    assert "EdHub360" in prompt
