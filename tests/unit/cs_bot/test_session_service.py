"""tests/unit/cs_bot/test_session_service.py"""
import json
import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage


class TestSerialize:

    def test_serializes_human_and_ai_messages(self):
        from cs_bot.app.services.session_service import _serialize
        msgs   = [HumanMessage(content="hi"), AIMessage(content="hello")]
        result = json.loads(_serialize(msgs))
        assert result[0] == {"type": "human", "content": "hi"}
        assert result[1] == {"type": "ai",    "content": "hello"}

    def test_empty_list_returns_empty_json_array(self):
        from cs_bot.app.services.session_service import _serialize
        assert json.loads(_serialize([])) == []

    def test_multiple_turns_serialized_in_order(self):
        from cs_bot.app.services.session_service import _serialize
        msgs   = [HumanMessage(content="q1"), AIMessage(content="a1"),
                  HumanMessage(content="q2"), AIMessage(content="a2")]
        result = json.loads(_serialize(msgs))
        assert len(result) == 4
        assert result[2]["content"] == "q2"


class TestDeserialize:

    def test_deserializes_human_message(self):
        from cs_bot.app.services.session_service import _deserialize
        data   = json.dumps([{"type": "human", "content": "hello"}])
        result = _deserialize(data)
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "hello"

    def test_deserializes_ai_message(self):
        from cs_bot.app.services.session_service import _deserialize
        data   = json.dumps([{"type": "ai", "content": "world"}])
        result = _deserialize(data)
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "world"

    def test_skips_unknown_message_types(self):
        from cs_bot.app.services.session_service import _deserialize
        data   = json.dumps([{"type": "system", "content": "ignored"}])
        result = _deserialize(data)
        assert result == []

    def test_round_trip_preserves_content(self):
        from cs_bot.app.services.session_service import _serialize, _deserialize
        msgs   = [HumanMessage(content="question"), AIMessage(content="answer")]
        result = _deserialize(_serialize(msgs))
        assert result[0].content == "question"
        assert result[1].content == "answer"

    def test_mixed_known_and_unknown_types(self):
        from cs_bot.app.services.session_service import _deserialize
        data   = json.dumps([
            {"type": "human",  "content": "hi"},
            {"type": "system", "content": "ignored"},
            {"type": "ai",     "content": "hello"},
        ])
        result = _deserialize(data)
        assert len(result) == 2
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)


class TestGetHistory:

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_data(self, mock_redis):
        mock_redis.get.return_value = None
        with patch("app.services.session_service.get_redis", return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            result = await get_history("sess_123")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_deserialized_messages(self, mock_redis):
        data = json.dumps([{"type": "human", "content": "hello"}])
        mock_redis.get.return_value = data
        with patch("app.services.session_service.get_redis", return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            result = await get_history("sess_123")
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "hello"

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_redis_error(self, mock_redis):
        mock_redis.get.side_effect = Exception("Redis down")
        with patch("app.services.session_service.get_redis", return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            result = await get_history("sess_123")
        assert result == []    # never raises

    @pytest.mark.asyncio
    async def test_uses_correct_redis_key(self, mock_redis):
        mock_redis.get.return_value = None
        with patch("app.services.session_service.get_redis", return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            await get_history("abc")
        mock_redis.get.assert_called_once_with("chat:abc")


class TestSaveHistory:

    @pytest.mark.asyncio
    async def test_calls_setex_with_correct_key(self, mock_redis):
        with patch("app.services.session_service.get_redis", return_value=mock_redis),              patch("app.services.session_service.settings") as s:
            s.SESSION_TTL_SECONDS = 3600
            from cs_bot.app.services.session_service import save_history
            await save_history("sess_123", [HumanMessage(content="hi")])
        args = mock_redis.setex.call_args[0]
        assert args[0] == "chat:sess_123"
        assert args[1] == 3600

    @pytest.mark.asyncio
    async def test_serializes_messages_as_json(self, mock_redis):
        with patch("app.services.session_service.get_redis", return_value=mock_redis),              patch("app.services.session_service.settings") as s:
            s.SESSION_TTL_SECONDS = 3600
            from cs_bot.app.services.session_service import save_history
            await save_history("sess_123", [HumanMessage(content="hi")])
        stored = mock_redis.setex.call_args[0][2]
        parsed = json.loads(stored)
        assert parsed[0]["content"] == "hi"

    @pytest.mark.asyncio
    async def test_does_not_raise_on_redis_error(self, mock_redis):
        mock_redis.setex.side_effect = Exception("Redis down")
        with patch("app.services.session_service.get_redis", return_value=mock_redis),              patch("app.services.session_service.settings") as s:
            s.SESSION_TTL_SECONDS = 3600
            from cs_bot.app.services.session_service import save_history
            await save_history("sess_123", [])    # must not raise


class TestDeleteHistory:

    @pytest.mark.asyncio
    async def test_deletes_correct_key(self, mock_redis):
        with patch("app.services.session_service.get_redis", return_value=mock_redis):
            from cs_bot.app.services.session_service import delete_history
            await delete_history("sess_abc")
        mock_redis.delete.assert_called_once_with("chat:sess_abc")

    @pytest.mark.asyncio
    async def test_does_not_raise_on_redis_error(self, mock_redis):
        mock_redis.delete.side_effect = Exception("Redis down")
        with patch("app.services.session_service.get_redis", return_value=mock_redis):
            from cs_bot.app.services.session_service import delete_history
            await delete_history("sess_abc")    # must not raise
