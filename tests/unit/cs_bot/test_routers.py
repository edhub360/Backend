"""tests/unit/cs_bot/test_routers.py"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from cs_bot.app.main import app

# Exact import paths based on actual router source code:
# chat.py   imports: get_history, save_history, delete_history (from session_service)
#                    generate_reply (from rag_service)
# ingestion.py imports: ingest_urls, ingest_json (from ingestion_service)
#                       settings (from core.config)
#           admin key:  x-admin-key HTTP header  → checked via _check_admin(x_admin_key)

CHAT_MOD = "cs_bot.app.routers.chat"
ING_MOD  = "cs_bot.app.routers.ingestion"


@pytest.fixture
def client():
    return AsyncClient(app=app, base_url="http://test")


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_returns_ok(self, client):
        async with client as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_service_name(self, client):
        async with client as ac:
            resp = await ac.get("/health")
        body = resp.json()
        assert "status" in body or "cs_bot" in str(body).lower()


# ─────────────────────────────────────────────────────────────────────────────
# Chat
# chat.py calls: get_history(session_id), generate_reply(message, history),
#                save_history(session_id, history), delete_history(session_id)
# All are awaited coroutines imported into the chat module — patch them there.
# ─────────────────────────────────────────────────────────────────────────────

class TestChatRouter:

    @pytest.mark.asyncio
    async def test_returns_reply_and_sources(self, client):
        with patch(f"{CHAT_MOD}.get_history",    new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",   new=AsyncMock()), \
             patch(f"{CHAT_MOD}.generate_reply", new=AsyncMock(return_value=("Hello", ["https://a.com"]))):
            async with client as ac:
                resp = await ac.post("/chat", json={"message": "hi"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "Hello"
        assert "https://a.com" in data["sources"]

    @pytest.mark.asyncio
    async def test_missing_message_returns_422(self, client):
        async with client as ac:
            resp = await ac.post("/chat", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generates_session_id_when_not_provided(self, client):
        with patch(f"{CHAT_MOD}.get_history",    new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",   new=AsyncMock()), \
             patch(f"{CHAT_MOD}.generate_reply", new=AsyncMock(return_value=("ok", []))):
            async with client as ac:
                resp = await ac.post("/chat", json={"message": "hi"})
        session_id = resp.json().get("session_id")
        assert session_id is not None and session_id != ""

    @pytest.mark.asyncio
    async def test_uses_provided_session_id(self, client):
        with patch(f"{CHAT_MOD}.get_history",    new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",   new=AsyncMock()), \
             patch(f"{CHAT_MOD}.generate_reply", new=AsyncMock(return_value=("ok", []))):
            async with client as ac:
                resp = await ac.post("/chat", json={"message": "hi", "session_id": "fixed-id"})
        assert resp.json()["session_id"] == "fixed-id"

    @pytest.mark.asyncio
    async def test_saves_history_after_reply(self, client):
        save_mock = AsyncMock()
        with patch(f"{CHAT_MOD}.get_history",    new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",   new=save_mock), \
             patch(f"{CHAT_MOD}.generate_reply", new=AsyncMock(return_value=("ok", []))):
            async with client as ac:
                await ac.post("/chat", json={"message": "hi"})
        save_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_history_appended_with_human_and_ai_messages(self, client):
        save_mock = AsyncMock()
        with patch(f"{CHAT_MOD}.get_history",    new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",   new=save_mock), \
             patch(f"{CHAT_MOD}.generate_reply", new=AsyncMock(return_value=("the answer", []))):
            async with client as ac:
                await ac.post("/chat", json={"message": "my question"})
        # chat.py: save_history(session_id, history)  → positional args [0] and [1]
        saved_messages = save_mock.call_args[0][1]
        types = [m.type for m in saved_messages]
        assert "human" in types
        assert "ai"    in types


# ─────────────────────────────────────────────────────────────────────────────
# Clear session
# DELETE /chat/session/{session_id}  →  await delete_history(session_id)
# ─────────────────────────────────────────────────────────────────────────────

class TestClearSession:

    @pytest.mark.asyncio
    async def test_returns_200_with_session_id(self, client):
        with patch(f"{CHAT_MOD}.delete_history", new=AsyncMock()):
            async with client as ac:
                resp = await ac.delete("/chat/session/abc123")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_calls_delete_history_with_correct_id(self, client):
        del_mock = AsyncMock()
        with patch(f"{CHAT_MOD}.delete_history", new=del_mock):
            async with client as ac:
                await ac.delete("/chat/session/my-session")
        # chat.py: await delete_history(session_id)
        del_mock.assert_awaited_once_with("my-session")


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion
# Admin key:  x-admin-key  HTTP request header  (FastAPI Header(...))
# _check_admin() compares x_admin_key against settings.ADMIN_KEY
# Patch settings.ADMIN_KEY inside the ingestion module so _check_admin passes.
#
# POST /ingest/urls  → background task (chunks_added always 0 in response)
# POST /ingest/json  → returns {"status": "ok", "chunks_ingested": count}
# ─────────────────────────────────────────────────────────────────────────────

class TestIngestionRouter:

    @pytest.mark.asyncio
    async def test_ingest_urls_missing_admin_key_returns_422(self, client):
        # No x-admin-key header → FastAPI Header(...) raises 422
        async with client as ac:
            resp = await ac.post("/ingest/urls", json={"urls": ["https://a.com"]})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_urls_wrong_key_returns_403(self, client):
        # x-admin-key provided but doesn't match settings.ADMIN_KEY → 403
        async with client as ac:
            resp = await ac.post(
                "/ingest/urls",
                json={"urls": ["https://a.com"]},
                headers={"x-admin-key": "wrong-key"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ingest_urls_correct_key_returns_200(self, client):
        # Patch settings.ADMIN_KEY so _check_admin passes
        with patch(f"{ING_MOD}.settings") as mock_settings:
            mock_settings.ADMIN_KEY = "test-secret"
            async with client as ac:
                resp = await ac.post(
                    "/ingest/urls",
                    json={"urls": ["https://a.com"]},
                    headers={"x-admin-key": "test-secret"},
                )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ingest_urls_returns_chunks_added_zero(self, client):
        # /ingest/urls uses BackgroundTasks → chunks_added is always 0 in the response
        with patch(f"{ING_MOD}.settings") as mock_settings:
            mock_settings.ADMIN_KEY = "test-secret"
            async with client as ac:
                resp = await ac.post(
                    "/ingest/urls",
                    json={"urls": ["https://a.com"]},
                    headers={"x-admin-key": "test-secret"},
                )
        assert resp.json()["chunks_added"] == 0

    @pytest.mark.asyncio
    async def test_ingest_json_wrong_key_returns_403(self, client):
        async with client as ac:
            resp = await ac.post(
                "/ingest/json",
                headers={"x-admin-key": "bad-key"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ingest_json_correct_key_returns_chunk_count(self, client):
        # /ingest/json returns {"status": "ok", "chunks_ingested": count}
        with patch(f"{ING_MOD}.ingest_json",  new=AsyncMock(return_value=3)), \
             patch(f"{ING_MOD}.settings") as mock_settings:
            mock_settings.ADMIN_KEY = "test-secret"
            async with client as ac:
                resp = await ac.post(
                    "/ingest/json",
                    headers={"x-admin-key": "test-secret"},
                )
        assert resp.status_code == 200
        assert resp.json()["chunks_ingested"] == 3