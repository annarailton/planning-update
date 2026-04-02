"""Shared logging configuration for backend and worker services.

Provides consistent colored logging output across services.

Usage:
    from packages.logging import get_logger, setup_logging

    # Setup logging (call once at service startup)
    setup_logging(log_level="INFO", debug=True)

    # Get a logger for your module
    logger = get_logger(__name__)
    logger.info("Service started")
"""

import logging
import os
import sys
import threading


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels in development.

    Note: Does not mutate the original log record to avoid issues with
    multiple handlers (e.g., file handler + console handler).
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Create a copy to avoid mutating the original record
        # This prevents color codes from leaking to other handlers
        if record.levelname in self.COLORS:
            record = logging.makeLogRecord(record.__dict__)
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
            )
        return super().format(record)


_logging_initialized = False
_logging_lock = threading.Lock()


def setup_logging(
    log_level: str | None = None,
    debug: bool | None = None,
) -> None:
    """Configure logging for the application (thread-safe).

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.
        debug: Enable colored output. Defaults to checking DEBUG env var.
    """
    global _logging_initialized

    # Fast path - already initialized
    if _logging_initialized:
        return

    with _logging_lock:
        # Double-check inside lock
        if _logging_initialized:
            return

        # Determine settings from args or environment
        if log_level is None:
            log_level = os.getenv("LOG_LEVEL", "INFO")
        if debug is None:
            debug = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

        # Get root logger
        root_logger = logging.getLogger()

        # Clear any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Set level with warning on invalid value
        level = getattr(logging, log_level.upper(), None)
        if level is None:
            print(
                f"Warning: Invalid LOG_LEVEL '{log_level}', using INFO",
                file=sys.stderr,
            )
            level = logging.INFO
        root_logger.setLevel(level)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Create formatter
        if debug:
            # Colored output for development
            formatter = ColoredFormatter(
                fmt="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            # Plain output for production
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Reduce noise from third-party libraries
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(
            logging.INFO if debug else logging.WARNING
        )

        _logging_initialized = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name, typically __name__

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


__all__ = [
    "setup_logging",
    "get_logger",
    "ColoredFormatter",
]
