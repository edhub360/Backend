"""tests/unit/cs_bot/test_session_service.py"""
import json
import pytest
from unittest.mock import AsyncMock, patch


def _msg_classes():
    from langchain_core.messages import HumanMessage, AIMessage
    return HumanMessage, AIMessage


# ─────────────────────────────────────────────────────────────────────────────
# _serialize
# ─────────────────────────────────────────────────────────────────────────────

class TestSerialize:

    def test_serializes_human_and_ai_messages(self):
        HumanMessage, AIMessage = _msg_classes()
        from cs_bot.app.services.session_service import _serialize

        messages = [HumanMessage(content="hello"), AIMessage(content="world")]
        result   = json.loads(_serialize(messages))

        assert result[0] == {"type": "human", "content": "hello"}
        assert result[1] == {"type": "ai",    "content": "world"}

    def test_multiple_turns_serialized_in_order(self):
        HumanMessage, AIMessage = _msg_classes()
        from cs_bot.app.services.session_service import _serialize

        messages = [
            HumanMessage(content="q1"),
            AIMessage(content="a1"),
            HumanMessage(content="q2"),
            AIMessage(content="a2"),
        ]
        result = json.loads(_serialize(messages))

        assert len(result) == 4
        assert result[0]["type"]    == "human"
        assert result[1]["type"]    == "ai"
        assert result[2]["content"] == "q2"
        assert result[3]["content"] == "a2"

    def test_empty_list_returns_empty_json_array(self):
        from cs_bot.app.services.session_service import _serialize
        assert _serialize([]) == "[]"


# ─────────────────────────────────────────────────────────────────────────────
# _deserialize
# ─────────────────────────────────────────────────────────────────────────────

class TestDeserialize:

    def test_deserializes_human_message(self):
        HumanMessage, AIMessage = _msg_classes()
        from cs_bot.app.services.session_service import _deserialize

        data   = json.dumps([{"type": "human", "content": "hi"}])
        result = _deserialize(data)

        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "hi"

    def test_deserializes_ai_message(self):
        HumanMessage, AIMessage = _msg_classes()
        from cs_bot.app.services.session_service import _deserialize

        data   = json.dumps([{"type": "ai", "content": "hello back"}])
        result = _deserialize(data)

        assert len(result) == 1
        assert isinstance(result[0], AIMessage)
        assert result[0].content == "hello back"

    def test_round_trip_preserves_content(self):
        HumanMessage, AIMessage = _msg_classes()
        from cs_bot.app.services.session_service import _serialize, _deserialize

        original = [HumanMessage(content="ping"), AIMessage(content="pong")]
        result   = _deserialize(_serialize(original))

        assert result[0].content == "ping"
        assert result[1].content == "pong"

    def test_mixed_known_and_unknown_types(self):
        HumanMessage, AIMessage = _msg_classes()
        from cs_bot.app.services.session_service import _deserialize

        # unknown type "system" is silently skipped per source code logic
        data = json.dumps([
            {"type": "human",  "content": "hi"},
            {"type": "system", "content": "ignored"},
            {"type": "ai",     "content": "bye"},
        ])
        result = _deserialize(data)

        assert len(result) == 2
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)


# ─────────────────────────────────────────────────────────────────────────────
# get_history
# ─────────────────────────────────────────────────────────────────────────────

class TestGetHistory:

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_data(self):
        mock_redis     = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            result = await get_history("sess_1")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_deserialized_messages(self):
        HumanMessage, AIMessage = _msg_classes()
        mock_redis     = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps([
            {"type": "human", "content": "hello"},
            {"type": "ai",    "content": "hi there"},
        ]))

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            result = await get_history("sess_1")

        assert len(result) == 2
        assert isinstance(result[0], HumanMessage)
        assert isinstance(result[1], AIMessage)

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_redis_error(self):
        mock_redis     = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            result = await get_history("sess_1")

        assert result == []

    @pytest.mark.asyncio
    async def test_uses_correct_redis_key(self):
        mock_redis     = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import get_history
            await get_history("abc123")

        mock_redis.get.assert_called_once_with("chat:abc123")


# ─────────────────────────────────────────────────────────────────────────────
# save_history
# ─────────────────────────────────────────────────────────────────────────────

class TestSaveHistory:

    @pytest.mark.asyncio
    async def test_calls_setex_with_correct_key(self):
        HumanMessage, _ = _msg_classes()
        mock_redis       = AsyncMock()
        mock_redis.setex = AsyncMock()

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import save_history
            await save_history("sess_1", [HumanMessage(content="hi")])

        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "chat:sess_1"

    @pytest.mark.asyncio
    async def test_serializes_messages_as_json(self):
        HumanMessage, AIMessage = _msg_classes()
        mock_redis       = AsyncMock()
        mock_redis.setex = AsyncMock()

        messages = [HumanMessage(content="q"), AIMessage(content="a")]

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import save_history
            await save_history("sess_1", messages)

        stored_json = mock_redis.setex.call_args[0][2]
        parsed      = json.loads(stored_json)
        assert parsed[0]["type"]    == "human"
        assert parsed[0]["content"] == "q"
        assert parsed[1]["type"]    == "ai"
        assert parsed[1]["content"] == "a"

    @pytest.mark.asyncio
    async def test_does_not_raise_on_redis_error(self):
        HumanMessage, _ = _msg_classes()
        mock_redis       = AsyncMock()
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis down"))

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import save_history
            await save_history("sess_1", [HumanMessage(content="hi")])
            # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# delete_history
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteHistory:

    @pytest.mark.asyncio
    async def test_deletes_correct_key(self):
        mock_redis        = AsyncMock()
        mock_redis.delete = AsyncMock()

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import delete_history
            await delete_history("sess_abc")

        mock_redis.delete.assert_called_once_with("chat:sess_abc")

    @pytest.mark.asyncio
    async def test_does_not_raise_on_redis_error(self):
        mock_redis        = AsyncMock()
        mock_redis.delete = AsyncMock(side_effect=Exception("Redis down"))

        with patch("cs_bot.app.services.session_service.get_redis",
                   return_value=mock_redis):
            from cs_bot.app.services.session_service import delete_history
            await delete_history("sess_abc")
            # must not raise