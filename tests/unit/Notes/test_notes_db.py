# tests/unit/notes/test_db.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/testdb"


# ══════════════════════════════════════════════════════════════════════════════
# Module-level configuration
# ══════════════════════════════════════════════════════════════════════════════
class TestDBConfiguration:

    @pytest.fixture(autouse=True)
    def patch_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", DATABASE_URL)

    def test_engine_created(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            mock_engine.assert_called_once()

    def test_engine_uses_database_url(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            args, kwargs = mock_engine.call_args
            assert args[0] == DATABASE_URL

    def test_engine_pool_size_is_5(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            _, kwargs = mock_engine.call_args
            assert kwargs["pool_size"] == 5

    def test_engine_max_overflow_is_10(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            _, kwargs = mock_engine.call_args
            assert kwargs["max_overflow"] == 10

    def test_engine_pool_pre_ping_enabled(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            _, kwargs = mock_engine.call_args
            assert kwargs["pool_pre_ping"] is True

    def test_engine_pool_timeout_is_30(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            _, kwargs = mock_engine.call_args
            assert kwargs["pool_timeout"] == 30

    def test_engine_pool_recycle_is_1800(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            _, kwargs = mock_engine.call_args
            assert kwargs["pool_recycle"] == 1800

    def test_engine_future_is_true(self):
        with patch("db.create_async_engine") as mock_engine:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            _, kwargs = mock_engine.call_args
            assert kwargs["future"] is True

    def test_async_session_local_created_with_engine(self):
        with patch("db.create_async_engine") as mock_engine, \
             patch("db.sessionmaker") as mock_sessionmaker:
            fake_engine = MagicMock(sync_engine=MagicMock())
            mock_engine.return_value = fake_engine
            import importlib, db
            importlib.reload(db)
            args, kwargs = mock_sessionmaker.call_args
            assert args[0] is fake_engine

    def test_session_expire_on_commit_false(self):
        with patch("db.create_async_engine") as mock_engine, \
             patch("db.sessionmaker") as mock_sessionmaker:
            mock_engine.return_value = MagicMock(sync_engine=MagicMock())
            import importlib, db
            importlib.reload(db)
            _, kwargs = mock_sessionmaker.call_args
            assert kwargs["expire_on_commit"] is False

    def test_base_is_declarative_base(self):
        import db
        from sqlalchemy.orm import DeclarativeBase, DeclarativeMeta
        # declarative_base() returns a class whose metaclass is DeclarativeMeta
        assert isinstance(db.Base, type)


# ══════════════════════════════════════════════════════════════════════════════
# set_search_path
# ══════════════════════════════════════════════════════════════════════════════
class TestSetSearchPath:

    def test_sets_search_path_to_stud_hub_schema(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("stud_hub_schema, public",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        from db import set_search_path
        set_search_path(dbapi_conn, MagicMock())

        set_cmd = cursor.execute.call_args_list[0][0][0]
        assert "stud_hub_schema" in set_cmd
        assert "public" in set_cmd

    def test_show_search_path_called(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("stud_hub_schema, public",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        from db import set_search_path
        set_search_path(dbapi_conn, MagicMock())

        executed_stmts = [c[0][0] for c in cursor.execute.call_args_list]
        assert any("SHOW search_path" in s for s in executed_stmts)

    def test_cursor_closed_after_execution(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("stud_hub_schema, public",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        from db import set_search_path
        set_search_path(dbapi_conn, MagicMock())

        cursor.close.assert_called_once()

    def test_fetchone_called_for_show_result(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("stud_hub_schema, public",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        from db import set_search_path
        set_search_path(dbapi_conn, MagicMock())

        cursor.fetchone.assert_called_once()

    def test_exactly_two_execute_calls(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("stud_hub_schema, public",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        from db import set_search_path
        set_search_path(dbapi_conn, MagicMock())

        assert cursor.execute.call_count == 2

    def test_prints_search_path_result(self, capsys):
        cursor = MagicMock()
        cursor.fetchone.return_value = ("stud_hub_schema, public",)
        dbapi_conn = MagicMock()
        dbapi_conn.cursor.return_value = cursor

        from db import set_search_path
        set_search_path(dbapi_conn, MagicMock())

        captured = capsys.readouterr().out
        assert "stud_hub_schema" in captured


# ══════════════════════════════════════════════════════════════════════════════
# get_session
# ══════════════════════════════════════════════════════════════════════════════
class TestGetSession:

    @pytest.mark.asyncio
    async def test_yields_session_object(self):
        mock_session = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("db.AsyncSessionLocal", return_value=mock_ctx):
            from db import get_session
            gen = get_session()
            session = await gen.__anext__()
            assert session is mock_session

    @pytest.mark.asyncio
    async def test_session_context_manager_entered(self):
        mock_session = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory = MagicMock(return_value=mock_ctx)

        with patch("db.AsyncSessionLocal", mock_factory):
            from db import get_session
            gen = get_session()
            await gen.__anext__()
            mock_factory.assert_called_once()
            mock_ctx.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_context_exited_after_generator_close(self):
        mock_session = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("db.AsyncSessionLocal", return_value=mock_ctx):
            from db import get_session
            gen = get_session()
            await gen.__anext__()
            try:
                await gen.aclose()
            except StopAsyncIteration:
                pass
            mock_ctx.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_is_async_generator(self):
        import inspect
        from db import get_session
        assert inspect.isasyncgenfunction(get_session)