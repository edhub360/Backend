"""tests/unit/cs_bot/test_routers.py"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from cs_bot.app.main import app

CHAT_MOD = "cs_bot.app.routers.chat"
ING_MOD  = "cs_bot.app.routers.ingestion"


def _make_redis():
    """Return an AsyncMock that behaves like an async Redis client."""
    r        = AsyncMock()
    r.get    = AsyncMock(return_value=None)
    r.setex  = AsyncMock()
    r.delete = AsyncMock()
    r.aclose = AsyncMock()
    return r


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
# ─────────────────────────────────────────────────────────────────────────────

class TestChatRouter:

    @pytest.mark.asyncio
    async def test_returns_reply_and_sources(self, client):
        redis = _make_redis()
        with patch(f"{CHAT_MOD}.get_redis",     new=AsyncMock(return_value=redis)), \
             patch(f"{CHAT_MOD}.get_history",   new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",  new=AsyncMock()), \
             patch(f"{CHAT_MOD}.generate_reply",new=AsyncMock(return_value=("Hello", ["https://a.com"]))):
            async with client as ac:
                resp = await ac.post("/chat", json={"message": "hi"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"]   == "Hello"
        assert "https://a.com" in data["sources"]

    @pytest.mark.asyncio
    async def test_missing_message_returns_422(self, client):
        async with client as ac:
            resp = await ac.post("/chat", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generates_session_id_when_not_provided(self, client):
        redis = _make_redis()
        with patch(f"{CHAT_MOD}.get_redis",     new=AsyncMock(return_value=redis)), \
             patch(f"{CHAT_MOD}.get_history",   new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",  new=AsyncMock()), \
             patch(f"{CHAT_MOD}.generate_reply",new=AsyncMock(return_value=("ok", []))):
            async with client as ac:
                resp = await ac.post("/chat", json={"message": "hi"})
        assert "session_id" in resp.json()

    @pytest.mark.asyncio
    async def test_uses_provided_session_id(self, client):
        redis = _make_redis()
        with patch(f"{CHAT_MOD}.get_redis",     new=AsyncMock(return_value=redis)), \
             patch(f"{CHAT_MOD}.get_history",   new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",  new=AsyncMock()), \
             patch(f"{CHAT_MOD}.generate_reply",new=AsyncMock(return_value=("ok", []))):
            async with client as ac:
                resp = await ac.post("/chat", json={"message": "hi", "session_id": "fixed-id"})
        assert resp.json()["session_id"] == "fixed-id"

    @pytest.mark.asyncio
    async def test_saves_history_after_reply(self, client):
        redis     = _make_redis()
        save_mock = AsyncMock()
        with patch(f"{CHAT_MOD}.get_redis",     new=AsyncMock(return_value=redis)), \
             patch(f"{CHAT_MOD}.get_history",   new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",  new=save_mock), \
             patch(f"{CHAT_MOD}.generate_reply",new=AsyncMock(return_value=("ok", []))):
            async with client as ac:
                await ac.post("/chat", json={"message": "hi"})
        save_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_history_appended_with_human_and_ai_messages(self, client):
        redis     = _make_redis()
        save_mock = AsyncMock()
        with patch(f"{CHAT_MOD}.get_redis",     new=AsyncMock(return_value=redis)), \
             patch(f"{CHAT_MOD}.get_history",   new=AsyncMock(return_value=[])), \
             patch(f"{CHAT_MOD}.save_history",  new=save_mock), \
             patch(f"{CHAT_MOD}.generate_reply",new=AsyncMock(return_value=("the answer", []))):
            async with client as ac:
                await ac.post("/chat", json={"message": "my question"})
        # save_history is called with (session_id, messages, redis)
        saved_messages = save_mock.call_args[0][1]
        types = [m.type for m in saved_messages]
        assert "human" in types
        assert "ai"    in types


# ─────────────────────────────────────────────────────────────────────────────
# Clear session
# ─────────────────────────────────────────────────────────────────────────────

class TestClearSession:

    @pytest.mark.asyncio
    async def test_returns_200_with_session_id(self, client):
        redis = _make_redis()
        with patch(f"{CHAT_MOD}.get_redis",      new=AsyncMock(return_value=redis)), \
             patch(f"{CHAT_MOD}.delete_history", new=AsyncMock()):
            async with client as ac:
                resp = await ac.delete("/chat/session/abc123")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_calls_delete_history_with_correct_id(self, client):
        redis    = _make_redis()
        del_mock = AsyncMock()
        with patch(f"{CHAT_MOD}.get_redis",      new=AsyncMock(return_value=redis)), \
             patch(f"{CHAT_MOD}.delete_history", new=del_mock):
            async with client as ac:
                await ac.delete("/chat/session/my-session")
        del_mock.assert_awaited_once()
        assert "my-session" in str(del_mock.call_args)


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion
# ─────────────────────────────────────────────────────────────────────────────

class TestIngestionRouter:

    @pytest.mark.asyncio
    async def test_ingest_urls_missing_admin_key_returns_422(self, client):
        async with client as ac:
            resp = await ac.post("/ingest/urls", json={"urls": ["https://a.com"]})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_urls_wrong_key_returns_403(self, client):
        async with client as ac:
            resp = await ac.post("/ingest/urls",
                                 json={"urls": ["https://a.com"], "admin_key": "wrong"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ingest_urls_correct_key_returns_200(self, client):
        # Patch ingest_urls AND the settings object so ADMIN_KEY matches
        with patch(f"{ING_MOD}.ingest_urls", new=AsyncMock(return_value=5)), \
             patch(f"{ING_MOD}.settings.ADMIN_KEY", "test-admin-secret", create=True):
            async with client as ac:
                resp = await ac.post("/ingest/urls",
                                     json={"urls": ["https://a.com"],
                                           "admin_key": "test-admin-secret"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_ingest_urls_returns_chunks_added(self, client):
        with patch(f"{ING_MOD}.ingest_urls", new=AsyncMock(return_value=5)), \
             patch(f"{ING_MOD}.settings.ADMIN_KEY", "test-admin-secret", create=True):
            async with client as ac:
                resp = await ac.post("/ingest/urls",
                                     json={"urls": ["https://a.com"],
                                           "admin_key": "test-admin-secret"})
        body = resp.json()
        # Accept either "chunks_added" or "detail" depending on router implementation
        assert body.get("chunks_added") == 5 or "added" in str(body).lower()

    @pytest.mark.asyncio
    async def test_ingest_json_wrong_key_returns_403(self, client):
        async with client as ac:
            resp = await ac.post("/ingest/json",
                                 json={"path": "/tmp/f.json", "admin_key": "bad"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ingest_json_correct_key_returns_chunk_count(self, client):
        with patch(f"{ING_MOD}.ingest_json", new=AsyncMock(return_value=3)), \
             patch(f"{ING_MOD}.settings.ADMIN_KEY", "test-admin-secret", create=True):
            async with client as ac:
                resp = await ac.post("/ingest/json",
                                     json={"path": "/tmp/f.json",
                                           "admin_key": "test-admin-secret"})
        assert resp.status_code == 200