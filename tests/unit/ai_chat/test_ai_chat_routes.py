"""
tests/unit/ai_chat/test_chat_router.py
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from io import BytesIO


# ---------------------------------------------------------------------------
# Minimal stubs for all external dependencies so nothing real is imported
# ---------------------------------------------------------------------------

# auth stub
mock_user = MagicMock()
mock_user.user_id = "test-user-123"

# session memory stub
mock_session_memory = MagicMock()
mock_session_memory.get_history.return_value = []
mock_session_memory.append_message.return_value = None

# gemini handler stub
mock_gemini = MagicMock()
mock_gemini.generate_response.return_value = "This is a mocked AI response."
mock_gemini.generate_image_answer = AsyncMock(return_value="Here is the solution: x = 42")

# faiss store stub
mock_faiss = MagicMock()
mock_faiss.index.ntotal = 1
mock_faiss.search.return_value = [
    ("chunk text about topic", "doc1.pdf", 0.92),
    ("another relevant chunk", "doc2.pdf", 0.85),
]

PATCHES = {
    "ai_chat.app.routes.chat.get_current_user": lambda: mock_user,
    "ai_chat.app.routes.chat.session_memory": mock_session_memory,
    "ai_chat.app.routes.chat.get_gemini_handler": lambda: mock_gemini,
    "ai_chat.app.routes.chat.get_faiss_store": lambda: mock_faiss,
    "ai_chat.app.routes.chat.embed_query": MagicMock(return_value=[0.1] * 768),
    "ai_chat.app.routes.chat.contains_harmful_content": MagicMock(return_value=False),
}


# ---------------------------------------------------------------------------
# autouse: patch all module-level globals in every test
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def apply_patches():
    # ← FIXED: full package path "ai_chat.app.routes.chat.*"
    with patch("ai_chat.app.routes.chat.session_memory", mock_session_memory), \
         patch("ai_chat.app.routes.chat.get_gemini_handler", return_value=mock_gemini), \
         patch("ai_chat.app.routes.chat.get_faiss_store", return_value=mock_faiss), \
         patch("ai_chat.app.routes.chat.embed_query", MagicMock(return_value=[0.1] * 768)), \
         patch("ai_chat.app.routes.chat.contains_harmful_content", MagicMock(return_value=False)):
        # Reset call counts before each test so assertions are isolated
        mock_gemini.generate_response.reset_mock()
        mock_session_memory.get_history.return_value = []
        mock_session_memory.append_message.reset_mock()
        yield


# ---------------------------------------------------------------------------
# client fixture — router-level app, auth bypassed via dependency_overrides
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    from ai_chat.app.routes.chat import router
    from ai_chat.app.utils.auth import get_current_user

    app = FastAPI()
    app.include_router(router, prefix="/chat")

    # Override the dependency — this is what actually bypasses auth
    app.dependency_overrides[get_current_user] = lambda: mock_user

    with patch("ai_chat.app.routes.chat.session_memory", mock_session_memory), \
         patch("ai_chat.app.routes.chat.get_gemini_handler", return_value=mock_gemini), \
         patch("ai_chat.app.routes.chat.get_faiss_store", return_value=mock_faiss), \
         patch("ai_chat.app.routes.chat.embed_query", return_value=[0.1] * 768), \
         patch("ai_chat.app.routes.chat.contains_harmful_content", return_value=False):
        yield TestClient(app)

    app.dependency_overrides.clear()


# ===========================================================================
# GET /chat/modes
# ===========================================================================

class TestGetChatModes:

    def test_modes_returns_200(self, client):
        response = client.get("/chat/modes")
        assert response.status_code == 200

    def test_modes_contains_general_and_rag(self, client):
        data = client.get("/chat/modes").json()
        values = [m["value"] for m in data["modes"]]
        assert "general" in values
        assert "rag" in values

    def test_modes_have_labels(self, client):
        data = client.get("/chat/modes").json()
        for mode in data["modes"]:
            assert "label" in mode
            assert len(mode["label"]) > 0


# ===========================================================================
# POST /chat — General mode
# ===========================================================================

class TestChatGeneralMode:

    def test_general_mode_returns_200(self, client):
        response = client.post("/chat", json={
            "query": "What is photosynthesis?",
            "mode": "general",
            "session_id": "sess-001"
        })
        assert response.status_code == 200

    def test_general_mode_answer_in_response(self, client):
        mock_gemini.generate_response.return_value = "Photosynthesis is the process..."
        response = client.post("/chat", json={
            "query": "What is photosynthesis?",
            "mode": "general"
        })
        assert "answer" in response.json()
        assert len(response.json()["answer"]) > 0

    def test_general_mode_no_retrieved_chunks(self, client):
        response = client.post("/chat", json={
            "query": "Tell me about history",
            "mode": "general"
        })
        assert response.json().get("retrieved_chunks") is None

    def test_general_mode_session_memory_called(self, client):
        mock_session_memory.get_history.return_value = []
        client.post("/chat", json={
            "query": "Hello",
            "mode": "general",
            "session_id": "sess-abc"
        })
        mock_session_memory.append_message.assert_called()

    def test_general_mode_with_existing_history(self, client):
        """History from previous turns is included as context."""
        prev_msg = MagicMock()
        prev_msg.content = "We were discussing Python."
        mock_session_memory.get_history.return_value = [prev_msg]

        response = client.post("/chat", json={
            "query": "Continue from where we left off.",
            "mode": "general",
            "session_id": "sess-history"
        })
        assert response.status_code == 200
        # Gemini was called with context that includes prior message
        call_args = mock_gemini.generate_response.call_args[0][0]
        assert "Python" in call_args

    # -----------------------------------------------------------------------
    # Long-text test — exceeds single query limit
    # -----------------------------------------------------------------------

    def test_long_query_general_mode(self, client):
        """
        A prompt >10 000 chars (simulating content exceeding a single
        query token window) must still return 200 — the handler is
        expected to pass it through to Gemini which handles chunking.
        """
        long_query = "Explain in extreme detail the following concept: " + (
            "Deep learning is a subset of machine learning that uses neural networks "
            "with many layers to learn representations of data. " * 120
        )
        assert len(long_query) > 10_000

        mock_gemini.generate_response.return_value = (
            "Deep learning uses hierarchical feature representations..."
        )

        response = client.post("/chat", json={
            "query": long_query,
            "mode": "general",
            "session_id": "sess-long"
        })
        assert response.status_code == 200
        assert response.json()["answer"] != ""

    def test_long_response_returned_fully(self, client):
        """LLM returning a very long answer is not truncated by the API."""
        long_answer = "This is part of the answer. " * 500   # ~14 000 chars
        mock_gemini.generate_response.return_value = long_answer

        response = client.post("/chat", json={
            "query": "Give me an exhaustive explanation.",
            "mode": "general"
        })
        assert response.status_code == 200
        assert response.json()["answer"] == long_answer

    def test_long_history_context_general_mode(self, client):
        """
        Many prior messages (simulating a long conversation) are all
        joined and passed as context without error.
        """
        history_msgs = []
        for i in range(50):
            m = MagicMock()
            m.content = f"Message number {i}: " + "word " * 40
            history_msgs.append(m)
        mock_session_memory.get_history.return_value = history_msgs

        response = client.post("/chat", json={
            "query": "Summarise our conversation.",
            "mode": "general",
            "session_id": "sess-long-history"
        })
        assert response.status_code == 200


# ===========================================================================
# POST /chat — RAG mode
# ===========================================================================

class TestChatRAGMode:

    def test_rag_mode_returns_200(self, client):
        mock_faiss.index.ntotal = 3
        mock_faiss.search.return_value = [
            ("relevant chunk 1", "notes.pdf", 0.95),
        ]
        response = client.post("/chat", json={
            "query": "What does the document say about tensors?",
            "mode": "rag"
        })
        assert response.status_code == 200

    def test_rag_mode_returns_retrieved_chunks(self, client):
        mock_faiss.index.ntotal = 2
        mock_faiss.search.return_value = [
            ("chunk about tensors", "ml_notes.pdf", 0.91),
            ("another chunk", "ml_notes.pdf", 0.80),
        ]
        response = client.post("/chat", json={
            "query": "Explain tensors",
            "mode": "rag"
        })
        chunks = response.json().get("retrieved_chunks")
        assert chunks is not None
        assert len(chunks) == 2

    def test_rag_mode_no_documents_returns_400(self, client):
        mock_faiss.index.ntotal = 0
        response = client.post("/chat", json={
            "query": "What is in the document?",
            "mode": "rag"
        })
        assert response.status_code == 400
        assert "No documents" in response.json()["detail"]

    def test_rag_mode_no_results_falls_back_to_general(self, client):
        mock_faiss.index.ntotal = 5
        mock_faiss.search.return_value = []   # empty search result
        mock_gemini.generate_response.return_value = "General fallback answer."

        response = client.post("/chat", json={
            "query": "Something not in docs",
            "mode": "rag"
        })
        assert response.status_code == 200
        assert "No relevant documents found" in response.json()["answer"]
        assert response.json()["retrieved_chunks"] == []

    def test_rag_long_query_embedding_called(self, client):
        """A long RAG query must still call embed_query with the full text."""
        mock_faiss.index.ntotal = 1
        mock_faiss.search.return_value = [("chunk", "doc.pdf", 0.9)]

        long_query = "Describe the concept in depth: " + "neural network " * 300
        assert len(long_query) > 5_000

        with patch("ai_chat.app.routes.chat.embed_query", return_value=[0.1] * 768) as mock_embed:
            response = client.post("/chat", json={
                "query": long_query,
                "mode": "rag"
            })
            assert response.status_code == 200
            mock_embed.assert_called_once_with(long_query)


# ===========================================================================
# Content moderation guardrail
# ===========================================================================

class TestContentModeration:

    def test_harmful_query_blocked_before_llm(self, client):
        with patch("ai_chat.app.routes.chat.contains_harmful_content", return_value=True):
            response = client.post("/chat", json={
                "query": "something harmful",
                "mode": "general"
            })
        assert response.status_code == 200
        assert "inappropriate content" in response.json()["answer"].lower()
        # Gemini must NOT have been called
        mock_gemini.generate_response.assert_not_called()

    def test_harmful_llm_output_replaced(self, client):
        mock_gemini.generate_response.return_value = "harmful output text"
        with patch("ai_chat.app.routes.chat.contains_harmful_content", side_effect=[False, True]):
            response = client.post("/chat", json={
                "query": "innocent query",
                "mode": "general"
            })
        assert "content policy" in response.json()["answer"].lower()


# ===========================================================================
# POST /chat/solve-image
# ===========================================================================

class TestSolveImage:

    def _png_bytes(self):
        # Minimal 1x1 white PNG
        return (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00'
            b'\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18'
            b'\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
        )

    def test_solve_image_returns_200(self, client):
        mock_gemini.generate_image_answer = AsyncMock(return_value="x = 42")
        response = client.post(
            "/chat/solve-image",
            files={"file": ("question.png", BytesIO(self._png_bytes()), "image/png")},
        )
        assert response.status_code == 200

    def test_solve_image_answer_in_response(self, client):
        mock_gemini.generate_image_answer = AsyncMock(return_value="The answer is 7.")
        response = client.post(
            "/chat/solve-image",
            files={"file": ("q.jpg", BytesIO(self._png_bytes()), "image/jpeg")},
        )
        assert response.json()["answer"] == "The answer is 7."

    def test_solve_image_invalid_content_type_rejected(self, client):
        response = client.post(
            "/chat/solve-image",
            files={"file": ("doc.pdf", BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
        assert response.status_code == 400
        assert "PNG" in response.json()["detail"] or "JPEG" in response.json()["detail"]

    def test_solve_image_empty_file_rejected(self, client):
        response = client.post(
            "/chat/solve-image",
            files={"file": ("empty.png", BytesIO(b""), "image/png")},
        )
        assert response.status_code == 400

    def test_solve_image_with_subject_and_mode(self, client):
        mock_gemini.generate_image_answer = AsyncMock(return_value="Step 1: ...")
        response = client.post(
            "/chat/solve-image",
            files={"file": ("q.png", BytesIO(self._png_bytes()), "image/png")},
            data={"subject": "physics", "mode": "steps"},
        )
        assert response.status_code == 200
        mock_gemini.generate_image_answer.assert_called_once()
        call_kwargs = mock_gemini.generate_image_answer.call_args[1]
        assert call_kwargs.get("subject") == "physics"
        assert call_kwargs.get("mode") == "steps"


# ===========================================================================
# POST /chat — invalid mode
# ===========================================================================

class TestInvalidMode:

    def test_invalid_mode_returns_400(self, client):
        response = client.post("/chat", json={
            "query": "Hello",
            "mode": "invalid_mode"
        })
        assert response.status_code == 422   # Pydantic rejects bad enum value
