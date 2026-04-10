"""tests/unit/cs_bot/test_routers.py — chat and ingestion routers + health endpoint"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport


def _get_app():
    """Return the FastAPI app with mocked startup dependencies."""
    import cs_bot.app.core.redis as redis_mod
    import cs_bot.app.core.database as db_mod

    mock_redis = MagicMock()
    mock_redis.aclose = AsyncMock()
    redis_mod.redis_client = mock_redis
    db_mod.vector_store = MagicMock()
    db_mod.embeddings = MagicMock()

    from cs_bot.app.main import app
    return app


class TestHealthEndpoint:

    @pytest.mark.asyncio
    async def test_returns_ok(self):
        app = _get_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_returns_service_name(self):
        app = _get_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        assert "service" in resp.json()


class TestChatRouter:

    @pytest.mark.asyncio
    async def test_returns_reply_and_sources(self):
        app = _get_app()
        with patch("cs_bot.app.services.session_service.get_history", new=AsyncMock(return_value=[])), \
             patch("cs_bot.app.services.rag_service.generate_reply", new=AsyncMock(return_value=("Hello!", ["https://edhub.com"]))), \
             patch("cs_bot.app.services.session_service.save_history", new=AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/chat", json={"message": "What is Edhub?"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["reply"] == "Hello!"
        assert data["sources"] == ["https://edhub.com"]

    @pytest.mark.asyncio
    async def test_generates_session_id_when_not_provided(self):
        app = _get_app()
        with patch("cs_bot.app.services.session_service.get_history", new=AsyncMock(return_value=[])), \
             patch("cs_bot.app.services.rag_service.generate_reply", new=AsyncMock(return_value=("r", []))), \
             patch("cs_bot.app.services.session_service.save_history", new=AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/chat", json={"message": "hi"})

        assert resp.json()["session_id"] is not None
        assert len(resp.json()["session_id"]) > 0

    @pytest.mark.asyncio
    async def test_uses_provided_session_id(self):
        app = _get_app()
        with patch("cs_bot.app.services.session_service.get_history", new=AsyncMock(return_value=[])), \
             patch("cs_bot.app.services.rag_service.generate_reply", new=AsyncMock(return_value=("r", []))), \
             patch("cs_bot.app.services.session_service.save_history", new=AsyncMock()):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/chat", json={"message": "hi", "session_id": "my-session"})

        assert resp.json()["session_id"] == "my-session"

    @pytest.mark.asyncio
    async def test_missing_message_returns_422(self):
        app = _get_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/chat", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_saves_history_after_reply(self):
        app = _get_app()
        mock_save = AsyncMock()
        with patch("cs_bot.app.services.session_service.get_history", new=AsyncMock(return_value=[])), \
             patch("cs_bot.app.services.rag_service.generate_reply", new=AsyncMock(return_value=("r", []))), \
             patch("cs_bot.app.services.session_service.save_history", new=mock_save):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                await ac.post("/chat", json={"message": "hi"})

        mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_history_appended_with_human_and_ai_messages(self):
        from langchain_core.messages import HumanMessage, AIMessage

        app = _get_app()
        saved = []

        async def capture_save(session_id, messages):
            saved.extend(messages)

        with patch("cs_bot.app.services.session_service.get_history", new=AsyncMock(return_value=[])), \
             patch("cs_bot.app.services.rag_service.generate_reply", new=AsyncMock(return_value=("answer", []))), \
             patch("cs_bot.app.services.session_service.save_history", new=capture_save):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                await ac.post("/chat", json={"message": "hello"})

        assert any(isinstance(m, HumanMessage) for m in saved)
        assert any(isinstance(m, AIMessage) for m in saved)


class TestClearSession:

    @pytest.mark.asyncio
    async def test_returns_200_with_session_id(self):
        app = _get_app()
        with patch("cs_bot.app.services.session_service.delete_history", new=AsyncMock()) as mock_del:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.delete("/chat/session/sess_abc")

        assert resp.status_code == 200
        assert resp.json()["session_id"] == "sess_abc"

    @pytest.mark.asyncio
    async def test_calls_delete_history_with_correct_id(self):
        app = _get_app()
        with patch("cs_bot.app.services.session_service.delete_history", new=AsyncMock()) as mock_del:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                await ac.delete("/chat/session/my_sess")

        mock_del.assert_called_once_with("my_sess")


class TestIngestionRouter:

    @pytest.mark.asyncio
    async def test_ingest_urls_missing_admin_key_returns_422(self):
        app = _get_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/ingest/urls", json={"urls": ["https://a.com"]})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_urls_wrong_key_returns_403(self):
        app = _get_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/ingest/urls",
                json={"urls": ["https://a.com"]},
                headers={"x-admin-key": "wrong"},
            )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ingest_urls_correct_key_returns_200(self):
        app = _get_app()
        with patch("cs_bot.app.routers.ingestion.ingest_urls", new=AsyncMock(return_value=3)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/ingest/urls",
                    json={"urls": ["https://a.com"]},
                    headers={"x-admin-key": "edhub360-admin-secret"},
                )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ingestion started in background"
        assert resp.json()["urls"] == ["https://a.com"]

    @pytest.mark.asyncio
    async def test_ingest_urls_returns_chunks_added_zero(self):
        app = _get_app()
        with patch("cs_bot.app.routers.ingestion.ingest_urls", new=AsyncMock(return_value=5)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/ingest/urls",
                    json={"urls": ["https://a.com"]},
                    headers={"x-admin-key": "edhub360-admin-secret"},
                )
        assert resp.json()["chunks_added"] == 0

    @pytest.mark.asyncio
    async def test_ingest_json_wrong_key_returns_403(self):
        app = _get_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/ingest/json", headers={"x-admin-key": "bad-key"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_ingest_json_correct_key_returns_chunk_count(self):
        app = _get_app()
        with patch("cs_bot.app.routers.ingestion.ingest_json", new=AsyncMock(return_value=10)):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/ingest/json",
                    headers={"x-admin-key": "edhub360-admin-secret"},
                )

        assert resp.status_code == 200
        assert resp.json()["chunks_ingested"] == 10
