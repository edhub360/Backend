def test_ai_chat_token_budget():
    from ai_chat.app.utils.prompt_builder import count_tokens  # fixed path

    prompt = "Hello world"
    assert count_tokens(prompt) < 20
