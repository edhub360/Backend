"""tests/unit/cs_bot/test_redis.py — init_redis and get_redis"""
import pytest
from unittest.mock import patch, MagicMock


class TestInitRedis:

    def test_converts_redis_url_to_tls(self):
        mock_client = MagicMock()
        with patch("cs_bot.app.core.redis.aioredis.from_url", return_value=mock_client) as mock_from_url,              patch("cs_bot.app.core.redis.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            import cs_bot.app.core.redis as redis_mod
            redis_mod.redis_client = None
            redis_mod.init_redis()
            call_url = mock_from_url.call_args[0][0]
            assert call_url.startswith("rediss://")

    def test_sets_global_client(self):
        mock_client = MagicMock()
        with patch("cs_bot.app.core.redis.aioredis.from_url", return_value=mock_client),              patch("cs_bot.app.core.redis.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379"
            import cs_bot.app.core.redis as redis_mod
            redis_mod.redis_client = None
            redis_mod.init_redis()
            assert redis_mod.redis_client is mock_client

    def test_passes_decode_responses_true(self):
        with patch("cs_bot.app.core.redis.aioredis.from_url") as mock_from_url,              patch("cs_bot.app.core.redis.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost"
            import cs_bot.app.core.redis as redis_mod
            redis_mod.init_redis()
            kwargs = mock_from_url.call_args[1]
            assert kwargs.get("decode_responses") is True

    def test_passes_retry_on_timeout(self):
        with patch("cs_bot.app.core.redis.aioredis.from_url") as mock_from_url,              patch("cs_bot.app.core.redis.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost"
            import cs_bot.app.core.redis as redis_mod
            redis_mod.init_redis()
            kwargs = mock_from_url.call_args[1]
            assert kwargs.get("retry_on_timeout") is True


class TestGetRedis:

    def test_returns_initialized_client(self):
        mock_client = MagicMock()
        import cs_bot.app.core.redis as redis_mod
        redis_mod.redis_client = mock_client
        assert redis_mod.get_redis() is mock_client

    def test_returns_none_before_init(self):
        import cs_bot.app.core.redis as redis_mod
        redis_mod.redis_client = None
        assert redis_mod.get_redis() is None
