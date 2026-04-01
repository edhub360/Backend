# tests/unit/notes/routes/test_notes_chat.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient

# ── Shared fixtures ────────────────────────────────────────────────────────────
NOTEBOOK_ID = uuid4()
USER_ID = "user_123"
SESSION_ID = f"{USER_ID}_{NOTEBOOK_ID}"

MOCK_CHUNKS = [
    {
        "source_id": str(uuid4()),
        "source_name": "lecture_notes.pdf",
        "chunk": "Python is a high-level programming language known for simplicity.",
        "score": 0.92,
    },
    {
        "source_id": str(uuid4()),
        "source_name": "textbook.pdf",
        "chunk": "It supports multiple programming paradigms including OOP.",
        "score": 0.85,
    },
]

MOCK_HISTORY = [
    {"role": "user", "content": "What is Python?"},
    {"role": "assistant", "content": "Python is a programming language."},
]


def make_app():
    """Build a fresh FastAPI app with all dependencies overridden."""
    from Notes.routes.chat import router

    app = FastAPI()
    app.include_router(router)

    mock_user = MagicMock()
    mock_user.user_id = USER_ID

    from Notes.utils.auth import get_current_user
    from Notes.db import get_session

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_session] = lambda: AsyncMock()

    return app


# ══════════════════════════════════════════════════════════════════════════════
# POST /{notebook_id}  — chat_with_notebook
# ══════════════════════════════════════════════════════════════════════════════
class TestChatWithNotebook:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.app = make_app()
        self.client = TestClient(self.app)
        self.url = f"/chat/{NOTEBOOK_ID}"
        self.payload = {"user_query": "What is Python?"}

    # ── happy path ─────────────────────────────────────────────────────────────

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_returns_200_on_success(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Python is great.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 200

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_response_contains_answer(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Python is great.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        resp = self.client.post(self.url, json=self.payload)
        assert resp.json()["answer"] == "Python is great."

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_response_contains_context_used(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        data = self.client.post(self.url, json=self.payload).json()
        assert "context_used" in data
        assert len(data["context_used"]) == 2

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_response_total_chunks_found(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        assert self.client.post(self.url, json=self.payload).json()["total_chunks_found"] == 2

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_response_notebook_id_matches(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        assert self.client.post(self.url, json=self.payload).json()["notebook_id"] == str(NOTEBOOK_ID)

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_context_snippet_truncated_at_300(self, mock_mem, mock_gemini, mock_chunks):
        long_chunk = {**MOCK_CHUNKS[0], "chunk": "A" * 500}
        mock_chunks.return_value = [long_chunk]
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        snippet = self.client.post(self.url, json=self.payload).json()["context_used"][0]["snippet"]
        assert snippet.endswith("...")
        assert len(snippet) == 303  # 300 chars + "..."

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_short_chunk_not_truncated(self, mock_mem, mock_gemini, mock_chunks):
        short_chunk = {**MOCK_CHUNKS[0], "chunk": "Short content."}
        mock_chunks.return_value = [short_chunk]
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        snippet = self.client.post(self.url, json=self.payload).json()["context_used"][0]["snippet"]
        assert snippet == "Short content."

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_adds_user_and_assistant_messages_to_memory(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        self.client.post(self.url, json=self.payload)
        calls = [str(c) for c in mock_mem.add_message.call_args_list]
        assert any("user" in c for c in calls)
        assert any("assistant" in c for c in calls)

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_max_tokens_capped_at_1024(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        self.client.post(self.url, json={**self.payload, "max_tokens": 9999})
        call_kwargs = mock_gemini.generate_contextual_response.call_args.kwargs
        assert call_kwargs["max_tokens"] <= 1024

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_default_max_context_chunks_is_5(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        self.client.post(self.url, json=self.payload)
        assert mock_chunks.call_args.kwargs["top_n"] == 5

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_custom_max_context_chunks_passed(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = []
        mock_mem.add_message = MagicMock()

        self.client.post(self.url, json={**self.payload, "max_context_chunks": 3})
        assert mock_chunks.call_args.kwargs["top_n"] == 3

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_existing_history_passed_to_gemini(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(return_value="Answer.")
        mock_mem.get_history.return_value = MOCK_HISTORY
        mock_mem.add_message = MagicMock()

        self.client.post(self.url, json=self.payload)
        call_kwargs = mock_gemini.generate_contextual_response.call_args.kwargs
        assert call_kwargs["chat_history"] == MOCK_HISTORY

    # ── error cases ────────────────────────────────────────────────────────────

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    def test_no_chunks_returns_404(self, mock_chunks):
        mock_chunks.return_value = []
        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 404
        assert "No content found" in resp.json()["detail"]

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    def test_chunk_retrieval_exception_returns_500(self, mock_chunks):
        mock_chunks.side_effect = RuntimeError("DB connection failed")
        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 500
        assert "Failed to retrieve content" in resp.json()["detail"]

    @patch("routes.chat.get_relevant_chunks_for_notebook", new_callable=AsyncMock)
    @patch("routes.chat.gemini_service")
    @patch("routes.chat.session_memory")
    def test_gemini_exception_returns_500(self, mock_mem, mock_gemini, mock_chunks):
        mock_chunks.return_value = MOCK_CHUNKS
        mock_gemini.generate_contextual_response = AsyncMock(side_effect=RuntimeError("Gemini down"))
        mock_mem.get_history.return_value = []

        resp = self.client.post(self.url, json=self.payload)
        assert resp.status_code == 500
        assert "Failed to generate response" in resp.json()["detail"]

    def test_invalid_notebook_uuid_returns_422(self):
        assert self.client.post("/chat/not-a-uuid", json=self.payload).status_code == 422

    def test_missing_user_query_returns_422(self):
        assert self.client.post(self.url, json={}).status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# GET /{notebook_id}/history
# ══════════════════════════════════════════════════════════════════════════════
class TestGetChatHistory:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(make_app())
        self.url = f"/chat/{NOTEBOOK_ID}/history"

    @patch("routes.chat.session_memory")
    def test_returns_200(self, mock_mem):
        mock_mem.get_history.return_value = MOCK_HISTORY
        assert self.client.get(self.url).status_code == 200

    @patch("routes.chat.session_memory")
    def test_returns_history_list(self, mock_mem):
        mock_mem.get_history.return_value = MOCK_HISTORY
        assert self.client.get(self.url).json() == MOCK_HISTORY

    @patch("routes.chat.session_memory")
    def test_empty_history_returns_empty_list(self, mock_mem):
        mock_mem.get_history.return_value = []
        assert self.client.get(self.url).json() == []

    @patch("routes.chat.session_memory")
    def test_session_id_uses_user_and_notebook(self, mock_mem):
        mock_mem.get_history.return_value = []
        self.client.get(self.url)
        called_session_id = mock_mem.get_history.call_args[0][0]
        assert USER_ID in called_session_id
        assert str(NOTEBOOK_ID) in called_session_id

    @patch("routes.chat.session_memory")
    def test_exception_returns_500(self, mock_mem):
        mock_mem.get_history.side_effect = RuntimeError("Memory error")
        resp = self.client.get(self.url)
        assert resp.status_code == 500
        assert "Failed to retrieve history" in resp.json()["detail"]

    def test_invalid_uuid_returns_422(self):
        assert self.client.get("/chat/bad-uuid/history").status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /{notebook_id}/history
# ══════════════════════════════════════════════════════════════════════════════
class TestClearChatHistory:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = TestClient(make_app())
        self.url = f"/chat/{NOTEBOOK_ID}/history"

    @patch("routes.chat.session_memory")
    def test_returns_200(self, mock_mem):
        mock_mem.clear_history = MagicMock()
        assert self.client.delete(self.url).status_code == 200

    @patch("routes.chat.session_memory")
    def test_returns_success_message(self, mock_mem):
        mock_mem.clear_history = MagicMock()
        assert self.client.delete(self.url).json()["message"] == "Chat history cleared successfully"

    @patch("routes.chat.session_memory")
    def test_clear_called_with_correct_session_id(self, mock_mem):
        mock_mem.clear_history = MagicMock()
        self.client.delete(self.url)
        called_session_id = mock_mem.clear_history.call_args[0][0]
        assert USER_ID in called_session_id
        assert str(NOTEBOOK_ID) in called_session_id

    @patch("routes.chat.session_memory")
    def test_exception_returns_500(self, mock_mem):
        mock_mem.clear_history.side_effect = RuntimeError("Clear failed")
        resp = self.client.delete(self.url)
        assert resp.status_code == 500
        assert "Failed to clear history" in resp.json()["detail"]

    def test_invalid_uuid_returns_422(self):
        assert self.client.delete("/chat/bad-uuid/history").status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Router registration
# ══════════════════════════════════════════════════════════════════════════════
class TestRouterConfig:

    def test_router_prefix_is_chat(self):
        from Notes.routes.chat import router
        assert router.prefix == "/chat"

    def test_router_tag_is_chat(self):
        from Notes.routes.chat import router
        assert "chat" in router.tags

    def test_post_route_exists(self):
        from Notes.routes.chat import router
        paths = [r.path for r in router.routes]
        assert "/{notebook_id}" in paths

    def test_history_routes_exist(self):
        from Notes.routes.chat import router
        paths = [r.path for r in router.routes]
        assert "/{notebook_id}/history" in paths