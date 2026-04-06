# tests/unit/notes/utils/test_logging.py

import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch, call


# ══════════════════════════════════════════════════════════════════════════════
# setup_logging
# ══════════════════════════════════════════════════════════════════════════════
class TestSetupLogging:

    def _make_app(self):
        app = MagicMock()
        app.middleware = MagicMock(return_value=lambda fn: fn)
        return app

    def test_registers_http_middleware(self):
        from utils.logging import setup_logging
        app = self._make_app()
        setup_logging(app)
        app.middleware.assert_called_once_with("http")

    def test_configures_logging_at_info_level(self):
        from utils.logging import setup_logging
        app = self._make_app()
        with patch("utils.logging.logging.basicConfig") as mock_basic:
            setup_logging(app)
            mock_basic.assert_called_once()
            _, kwargs = mock_basic.call_args
            assert kwargs.get("level") == logging.INFO

    def test_log_format_contains_expected_fields(self):
        from utils.logging import setup_logging
        app = self._make_app()
        with patch("utils.logging.logging.basicConfig") as mock_basic:
            setup_logging(app)
            _, kwargs = mock_basic.call_args
            fmt = kwargs.get("format", "")
            assert "%(asctime)s" in fmt
            assert "%(name)s" in fmt
            assert "%(levelname)s" in fmt
            assert "%(message)s" in fmt

    def test_returns_none(self):
        from utils.logging import setup_logging
        app = self._make_app()
        assert setup_logging(app) is None


# ══════════════════════════════════════════════════════════════════════════════
# log_requests middleware
# ══════════════════════════════════════════════════════════════════════════════
class TestLogRequestsMiddleware:

    def _capture_middleware(self):
        """Register setup_logging on a real FastAPI-style mock and capture the middleware fn."""
        captured = {}

        app = MagicMock()

        def fake_middleware(kind):
            def decorator(fn):
                captured["fn"] = fn
                return fn
            return decorator

        app.middleware = fake_middleware

        from utils.logging import setup_logging
        setup_logging(app)
        return captured["fn"]

    @pytest.mark.asyncio
    async def test_middleware_calls_call_next(self):
        middleware = self._capture_middleware()

        request = MagicMock()
        request.method = "GET"
        request.url = "http://localhost/test"

        response = MagicMock()
        response.status_code = 200
        call_next = AsyncMock(return_value=response)

        await middleware(request, call_next)
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_middleware_returns_response(self):
        middleware = self._capture_middleware()

        request = MagicMock()
        request.method = "POST"
        request.url = "http://localhost/api"

        response = MagicMock()
        response.status_code = 201
        call_next = AsyncMock(return_value=response)

        result = await middleware(request, call_next)
        assert result is response

    @pytest.mark.asyncio
    async def test_middleware_prints_method(self, capsys):
        middleware = self._capture_middleware()

        request = MagicMock()
        request.method = "DELETE"
        request.url = "http://localhost/resource/1"

        response = MagicMock()
        response.status_code = 204
        call_next = AsyncMock(return_value=response)

        await middleware(request, call_next)
        captured = capsys.readouterr().out
        assert "DELETE" in captured

    @pytest.mark.asyncio
    async def test_middleware_prints_url(self, capsys):
        middleware = self._capture_middleware()

        request = MagicMock()
        request.method = "GET"
        request.url = "http://localhost/notebooks"

        response = MagicMock()
        response.status_code = 200
        call_next = AsyncMock(return_value=response)

        await middleware(request, call_next)
        captured = capsys.readouterr().out
        assert "http://localhost/notebooks" in captured

    @pytest.mark.asyncio
    async def test_middleware_prints_status_code(self, capsys):
        middleware = self._capture_middleware()

        request = MagicMock()
        request.method = "GET"
        request.url = "http://localhost/test"

        response = MagicMock()
        response.status_code = 404
        call_next = AsyncMock(return_value=response)

        await middleware(request, call_next)
        captured = capsys.readouterr().out
        assert "404" in captured

    @pytest.mark.asyncio
    async def test_middleware_prints_all_three_parts(self, capsys):
        middleware = self._capture_middleware()

        request = MagicMock()
        request.method = "PATCH"
        request.url = "http://localhost/sources/abc"

        response = MagicMock()
        response.status_code = 500
        call_next = AsyncMock(return_value=response)

        await middleware(request, call_next)
        captured = capsys.readouterr().out
        assert "PATCH" in captured
        assert "http://localhost/sources/abc" in captured
        assert "500" in captured

    @pytest.mark.asyncio
    async def test_response_returned_even_on_error_status(self):
        middleware = self._capture_middleware()

        request = MagicMock()
        request.method = "GET"
        request.url = "http://localhost/fail"

        response = MagicMock()
        response.status_code = 500
        call_next = AsyncMock(return_value=response)

        result = await middleware(request, call_next)
        assert result is response