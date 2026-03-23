def test_ai_chat_token_budget():
    from app.modules.ai_chat.prompt_builder import count_tokens

    prompt = "Hello world"
    assert count_tokens(prompt) < 20
