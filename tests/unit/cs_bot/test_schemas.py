"""tests/unit/cs_bot/test_schemas.py — Pydantic schema validation"""
import pytest
from pydantic import ValidationError
from cs_bot.app.models.schemas import ChatRequest, ChatResponse, IngestRequest, IngestResponse


class TestChatRequest:

    def test_message_is_required(self):
        with pytest.raises(ValidationError):
            ChatRequest()

    def test_session_id_defaults_to_none(self):
        req = ChatRequest(message="hello")
        assert req.session_id is None

    def test_session_id_can_be_set(self):
        req = ChatRequest(message="hello", session_id="abc-123")
        assert req.session_id == "abc-123"

    def test_message_is_stored(self):
        req = ChatRequest(message="what is edhub?")
        assert req.message == "what is edhub?"


class TestChatResponse:

    def test_missing_sources_raises(self):
        with pytest.raises(ValidationError):
            ChatResponse(session_id="s1", reply="hi")

    def test_valid_response(self):
        resp = ChatResponse(session_id="s1", reply="hi", sources=["https://example.com"])
        assert resp.session_id == "s1"
        assert resp.reply      == "hi"
        assert resp.sources    == ["https://example.com"]

    def test_empty_sources_allowed(self):
        resp = ChatResponse(session_id="s1", reply="hi", sources=[])
        assert resp.sources == []

    def test_missing_reply_raises(self):
        with pytest.raises(ValidationError):
            ChatResponse(session_id="s1", sources=[])


class TestIngestRequest:

    def test_urls_required(self):
        with pytest.raises(ValidationError):
            IngestRequest()

    def test_urls_stored(self):
        req = IngestRequest(urls=["https://a.com", "https://b.com"])
        assert len(req.urls) == 2

    def test_empty_urls_allowed(self):
        req = IngestRequest(urls=[])
        assert req.urls == []


class TestIngestResponse:

    def test_valid_response(self):
        resp = IngestResponse(status="ok", urls=["https://a.com"], chunks_added=5)
        assert resp.chunks_added == 5
        assert resp.status       == "ok"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            IngestResponse(status="ok", urls=["https://a.com"])
