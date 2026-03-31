# tests/unit/ai_chat/test_gemini_handler.py

import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_response(text: str) -> MagicMock:
    mock = MagicMock()
    mock.text = text
    return mock


def make_handler(model_name: str = "gemini-2.5-pro"):
    """Create a GeminiHandler with genai.GenerativeModel patched out."""
    from ai_chat.app.utils.gemini_handler import GeminiHandler

    with patch("ai_chat.app.utils.gemini_handler.genai.GenerativeModel") as mock_model_cls:
        mock_model_cls.return_value = MagicMock()
        handler = GeminiHandler(model_name=model_name)
    return handler


# ─────────────────────────────────────────────
# GeminiHandler.__init__
# ─────────────────────────────────────────────

class TestGeminiHandlerInit:

    def test_stores_model_name(self):
        handler = make_handler("gemini-2.5-pro")
        assert handler.model_name == "gemini-2.5-pro"

    def test_model_is_initialized(self):
        handler = make_handler()
        assert handler.model is not None

    def test_custom_model_name_stored(self):
        handler = make_handler("gemini-1.5-flash")
        assert handler.model_name == "gemini-1.5-flash"

    def test_generative_model_called_with_model_name(self):
        from ai_chat.app.utils.gemini_handler import GeminiHandler

        with patch("ai_chat.app.utils.gemini_handler.genai.GenerativeModel") as mock_cls:
            mock_cls.return_value = MagicMock()
            GeminiHandler(model_name="gemini-1.5-flash")

        mock_cls.assert_called_once_with("gemini-1.5-flash")


# ─────────────────────────────────────────────
# generate_response — general mode (no context)
# ─────────────────────────────────────────────

class TestGenerateResponseGeneral:

    def test_returns_model_text(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("Hello! How can I help?")

        result = handler.generate_response("hi")

        assert result == "Hello! How can I help?"

    def test_calls_generate_content_once(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("what is python?")

        handler.model.generate_content.assert_called_once()

    def test_prompt_contains_user_query(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("explain recursion")

        prompt = handler.model.generate_content.call_args[0][0]
        assert "explain recursion" in prompt

    def test_prompt_contains_smartstudy_identity(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("hello")

        prompt = handler.model.generate_content.call_args[0][0]
        assert "SmartStudy" in prompt

    def test_none_context_uses_general_mode(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("hello", context=None)

        prompt = handler.model.generate_content.call_args[0][0]
        # General mode prompt does NOT include "Context Documents:"
        assert "Context Documents:" not in prompt

    def test_empty_response_text_returns_fallback(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("")

        result = handler.generate_response("test")

        assert result == "I apologize, but I couldn't generate a response."

    def test_none_response_text_returns_fallback(self):
        handler = make_handler()
        mock_resp = MagicMock()
        mock_resp.text = None
        handler.model.generate_content.return_value = mock_resp

        result = handler.generate_response("test")

        assert result == "I apologize, but I couldn't generate a response."

    def test_exception_returns_error_string(self):
        handler = make_handler()
        handler.model.generate_content.side_effect = Exception("quota exceeded")

        result = handler.generate_response("hello")

        assert "Sorry, I encountered an error" in result
        assert "quota exceeded" in result

    def test_exception_does_not_raise(self):
        handler = make_handler()
        handler.model.generate_content.side_effect = RuntimeError("network error")

        result = handler.generate_response("hello")

        assert isinstance(result, str)


# ─────────────────────────────────────────────
# generate_response — RAG mode (with context)
# ─────────────────────────────────────────────

class TestGenerateResponseRAG:

    def test_context_included_in_prompt(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("answer")

        handler.generate_response("what is ML?", context=["ML is machine learning."])

        prompt = handler.model.generate_content.call_args[0][0]
        assert "ML is machine learning." in prompt

    def test_prompt_contains_context_documents_header(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("query", context=["some doc"])

        prompt = handler.model.generate_content.call_args[0][0]
        assert "Context Documents:" in prompt

    def test_prompt_labels_multiple_documents(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response(
            "query",
            context=["first doc", "second doc", "third doc"]
        )

        prompt = handler.model.generate_content.call_args[0][0]
        assert "Document 1:" in prompt
        assert "Document 2:" in prompt
        assert "Document 3:" in prompt

    def test_all_context_documents_present_in_prompt(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        docs = ["alpha content", "beta content", "gamma content"]
        handler.generate_response("query", context=docs)

        prompt = handler.model.generate_content.call_args[0][0]
        for doc in docs:
            assert doc in prompt

    def test_user_query_present_in_rag_prompt(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("explain gradient descent", context=["some doc"])

        prompt = handler.model.generate_content.call_args[0][0]
        assert "explain gradient descent" in prompt

    def test_rag_prompt_contains_user_question_label(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("my question", context=["doc"])

        prompt = handler.model.generate_content.call_args[0][0]
        assert "User Question:" in prompt

    def test_empty_context_list_uses_general_mode(self):
        """Empty list is falsy — falls through to general mode, not RAG."""
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        handler.generate_response("hello", context=[])

        prompt = handler.model.generate_content.call_args[0][0]
        assert "Context Documents:" not in prompt

    def test_rag_exception_returns_error_string(self):
        handler = make_handler()
        handler.model.generate_content.side_effect = Exception("timeout")

        result = handler.generate_response("query", context=["doc"])

        assert "Sorry, I encountered an error" in result
        assert "timeout" in result

    def test_returns_model_text_in_rag_mode(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("RAG answer here")

        result = handler.generate_response("q", context=["doc1"])

        assert result == "RAG answer here"


# ─────────────────────────────────────────────
# generate_image_answer
# ─────────────────────────────────────────────

class TestGenerateImageAnswer:

    @pytest.mark.anyio
    async def test_returns_model_text(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("Step 1: ...")

        result = await handler.generate_image_answer(b"fake_image_bytes")

        assert result == "Step 1: ..."

    @pytest.mark.anyio
    async def test_calls_generate_content_with_image_bytes(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("answer")

        await handler.generate_image_answer(b"imgdata")

        args = handler.model.generate_content.call_args[0][0]
        # Must contain inline_data with our image bytes
        parts = args[0]["parts"]
        inline = next(p for p in parts if "inline_data" in p)
        assert inline["inline_data"]["data"] == b"imgdata"

    @pytest.mark.anyio
    async def test_default_mode_is_steps(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        await handler.generate_image_answer(b"img")

        args = handler.model.generate_content.call_args[0][0]
        instruction = args[0]["parts"][0]["text"]
        assert "step by step" in instruction.lower()

    @pytest.mark.anyio
    async def test_final_mode_instruction(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        await handler.generate_image_answer(b"img", mode="final")

        args = handler.model.generate_content.call_args[0][0]
        instruction = args[0]["parts"][0]["text"]
        assert "1–2 concise sentences" in instruction or "1-2" in instruction

    @pytest.mark.anyio
    async def test_steps_mode_instruction(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        await handler.generate_image_answer(b"img", mode="steps")

        args = handler.model.generate_content.call_args[0][0]
        instruction = args[0]["parts"][0]["text"]
        assert "final answer" in instruction.lower()

    @pytest.mark.anyio
    async def test_subject_appended_to_instruction(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        await handler.generate_image_answer(b"img", subject="Physics")

        args = handler.model.generate_content.call_args[0][0]
        instruction = args[0]["parts"][0]["text"]
        assert "Physics" in instruction

    @pytest.mark.anyio
    async def test_no_subject_instruction_has_no_subject_line(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        await handler.generate_image_answer(b"img", subject=None)

        args = handler.model.generate_content.call_args[0][0]
        instruction = args[0]["parts"][0]["text"]
        assert "The subject is" not in instruction

    @pytest.mark.anyio
    async def test_mime_type_is_image_png(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        await handler.generate_image_answer(b"img")

        args = handler.model.generate_content.call_args[0][0]
        parts = args[0]["parts"]
        inline = next(p for p in parts if "inline_data" in p)
        assert inline["inline_data"]["mime_type"] == "image/png"

    @pytest.mark.anyio
    async def test_empty_response_text_returns_fallback(self):
        handler = make_handler()
        mock_resp = MagicMock()
        mock_resp.text = ""
        handler.model.generate_content.return_value = mock_resp

        result = await handler.generate_image_answer(b"img")

        assert result == "I could not generate an answer from the image."

    @pytest.mark.anyio
    async def test_exception_returns_error_string(self):
        handler = make_handler()
        handler.model.generate_content.side_effect = Exception("vision API down")

        result = await handler.generate_image_answer(b"img")

        assert "Sorry, I encountered an error while processing the image" in result
        assert "vision API down" in result

    @pytest.mark.anyio
    async def test_exception_does_not_raise(self):
        handler = make_handler()
        handler.model.generate_content.side_effect = RuntimeError("crash")

        result = await handler.generate_image_answer(b"img")

        assert isinstance(result, str)

    @pytest.mark.anyio
    async def test_role_is_user(self):
        handler = make_handler()
        handler.model.generate_content.return_value = make_response("ok")

        await handler.generate_image_answer(b"img")

        args = handler.model.generate_content.call_args[0][0]
        assert args[0]["role"] == "user"


# ─────────────────────────────────────────────
# get_gemini_handler (singleton)
# ─────────────────────────────────────────────

class TestGetGeminiHandler:

    def test_returns_gemini_handler_instance(self):
        from ai_chat.app.utils.gemini_handler import GeminiHandler

        with patch("ai_chat.app.utils.gemini_handler._gemini_handler", None):
            with patch("ai_chat.app.utils.gemini_handler.genai.GenerativeModel"):
                from ai_chat.app.utils.gemini_handler import get_gemini_handler
                handler = get_gemini_handler()

        assert isinstance(handler, GeminiHandler)

    def test_returns_same_instance_on_repeated_calls(self):
        with patch("ai_chat.app.utils.gemini_handler._gemini_handler", None):
            with patch("ai_chat.app.utils.gemini_handler.genai.GenerativeModel"):
                from ai_chat.app.utils.gemini_handler import get_gemini_handler
                h1 = get_gemini_handler()
                h2 = get_gemini_handler()

        assert h1 is h2

    def test_existing_instance_reused_without_recreating(self):
        from ai_chat.app.utils.gemini_handler import GeminiHandler

        existing = make_handler()

        with patch("ai_chat.app.utils.gemini_handler._gemini_handler", existing):
            with patch("ai_chat.app.utils.gemini_handler.genai.GenerativeModel") as mock_cls:
                from ai_chat.app.utils.gemini_handler import get_gemini_handler
                result = get_gemini_handler()

        mock_cls.assert_not_called()
        assert result is existing