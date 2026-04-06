# tests/unit/courses/test_utils.py

import logging
import pytest
import sys
from unittest.mock import patch


# ─────────────────────────────────────────────
# setup_logging  (app/utils/logging.py)
# ─────────────────────────────────────────────

class TestSetupLogging:

    @pytest.fixture(autouse=True)
    def reset_root_logger(self):
        """
        Isolate every test from root logger level changes made by setup_logging().
        Without this, test_log_level_from_env_debug sets root to DEBUG and all
        subsequent assertions against INFO/WARNING/ERROR will read the stale level.
        """
        original_level = logging.getLogger().level
        yield
        logging.getLogger().setLevel(original_level)

    @pytest.fixture(autouse=True)
    def reload_logging_module(self):
        """
        setup_logging() is typically called once at app startup. Python caches
        the module, so a second import inside the same test session won't re-run
        module-level code. Popping from sys.modules forces a fresh import each
        test, which is required for the basicConfig mock test to work correctly.
        """
        sys.modules.pop("courses.app.utils.logging", None)
        yield
        sys.modules.pop("courses.app.utils.logging", None)

    # ── Structural tests ──────────────────────

    def test_returns_logger_instance(self):
        from courses.app.utils.logging import setup_logging
        logger = setup_logging()
        assert isinstance(logger, logging.Logger)

    def test_logger_name_is_course_backend(self):
        from courses.app.utils.logging import setup_logging
        logger = setup_logging()
        assert logger.name == "course_backend"

    def test_returns_same_logger_on_repeated_calls(self):
        from courses.app.utils.logging import setup_logging
        logger1 = setup_logging()
        logger2 = setup_logging()
        assert logger1 is logger2  # logging.getLogger() returns cached instance

    def test_logger_can_emit_info(self):
        from courses.app.utils.logging import setup_logging
        logger = setup_logging()
        logger.info("test info message")  # should not raise

    def test_logger_can_emit_error(self):
        from courses.app.utils.logging import setup_logging
        logger = setup_logging()
        logger.error("test error message")  # should not raise

    # ── Log level tests ───────────────────────

    def test_default_log_level_is_info(self):
        import os
        os.environ.pop("LOG_LEVEL", None)
        with patch.dict("os.environ", {}, clear=False):
            from courses.app.utils.logging import setup_logging
            setup_logging()
        assert logging.getLogger().level == logging.INFO

    def test_log_level_from_env_debug(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "DEBUG"}):
            from courses.app.utils.logging import setup_logging
            setup_logging()
        assert logging.getLogger().level == logging.DEBUG

    def test_log_level_from_env_warning(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "WARNING"}):
            from courses.app.utils.logging import setup_logging
            setup_logging()
        assert logging.getLogger().level == logging.WARNING

    def test_log_level_from_env_error(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "ERROR"}):
            from courses.app.utils.logging import setup_logging
            setup_logging()
        assert logging.getLogger().level == logging.ERROR

    def test_log_level_env_is_case_insensitive(self):
        with patch.dict("os.environ", {"LOG_LEVEL": "debug"}):
            from courses.app.utils.logging import setup_logging
            setup_logging()
        assert logging.getLogger().level == logging.DEBUG

    # ── logging implementation test ───────────────

    def test_root_logger_level_set_to_info_by_default(self):
        import logging
        root = logging.getLogger()
        root.handlers.clear()  # allow setLevel to be observed cleanly
        from courses.app.utils.logging import setup_logging
        setup_logging()
        assert root.level == logging.INFO

    def test_root_logger_level_respects_env_var(self, monkeypatch):
        import logging
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        root = logging.getLogger()
        root.handlers.clear()
        from courses.app.utils.logging import setup_logging
        setup_logging()
        assert root.level == logging.DEBUG

    def test_returns_named_logger(self):
        from courses.app.utils.logging import setup_logging
        logger = setup_logging()
        assert logger.name == "course_backend"


# ─────────────────────────────────────────────
# validate_pagination  (app/utils/pagination.py)
# ─────────────────────────────────────────────

class TestValidatePagination:

    @pytest.fixture(autouse=True)
    def import_fn(self):
        from courses.app.utils.pagination import validate_pagination
        self.validate = validate_pagination

    # ── Happy path ────────────────────────────

    def test_valid_defaults_no_exception(self):
        self.validate(1, 10)

    def test_valid_page_and_limit(self):
        self.validate(5, 50, 100)

    def test_boundary_page_1_passes(self):
        self.validate(1, 1)

    def test_boundary_limit_equals_max_passes(self):
        self.validate(1, 100, 100)

    def test_custom_max_page_limit_passes(self):
        self.validate(1, 200, 200)

    def test_large_page_number_passes(self):
        self.validate(9999, 10, 100)

    def test_returns_none(self):
        result = self.validate(1, 10, 100)
        assert result is None

    # ── Page validation ───────────────────────

    def test_page_zero_raises(self):
        with pytest.raises(ValueError, match="Page must be >= 1"):
            self.validate(0, 10)

    def test_page_negative_raises(self):
        with pytest.raises(ValueError, match="Page must be >= 1"):
            self.validate(-5, 10)

    # ── Limit validation ──────────────────────

    def test_limit_zero_raises(self):
        with pytest.raises(ValueError, match="Limit must be in"):
            self.validate(1, 0)

    def test_limit_negative_raises(self):
        with pytest.raises(ValueError, match="Limit must be in"):
            self.validate(1, -1)

    def test_limit_exceeds_max_raises(self):
        with pytest.raises(ValueError, match="Limit must be in"):
            self.validate(1, 101, 100)

    def test_limit_exceeds_custom_max_raises(self):
        with pytest.raises(ValueError, match="Limit must be in"):
            self.validate(1, 51, 50)

    def test_error_message_contains_max_value(self):
        with pytest.raises(ValueError) as exc:
            self.validate(1, 999, 50)
        assert "50" in str(exc.value)

    # ── Both invalid ──────────────────────────

    def test_page_checked_before_limit(self):
        """page=0 error raised even when limit is also invalid."""
        with pytest.raises(ValueError, match="Page must be >= 1"):
            self.validate(0, 0)

    # ── Default max_page_limit ────────────────

    def test_default_max_is_100(self):
        self.validate(1, 100)  # passes with default max

    def test_limit_101_fails_with_default_max(self):
        with pytest.raises(ValueError):
            self.validate(1, 101)