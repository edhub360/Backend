import pytest
from unittest.mock import MagicMock


@pytest.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    from ai_chat.app.main import app as ai_chat_app

    async with AsyncClient(
        transport=ASGITransport(app=ai_chat_app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def mock_ai_chat_service(monkeypatch):
    mock_service = MagicMock()
    mock_service.get_response = MagicMock(return_value="Mocked AI response")
    mock_service.stream_response = MagicMock(return_value=iter(["Mocked", " stream"]))
    monkeypatch.setattr(
        "ai_chat.app.modules.ai_chat.router.AIChatService",
        MagicMock(return_value=mock_service)
    )
    return mock_service