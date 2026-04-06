import logging
import os


def setup_logging():
    level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    # FIXED: set root logger level directly — works even if handlers already exist
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Only add handler if none exist (avoids duplicate logs in production)
    if not root_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s'
        ))
        root_logger.addHandler(handler)

    return logging.getLogger("course_backend")