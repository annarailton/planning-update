"""Logging configuration with colored output for development.

Re-exports from shared packages/logging and initializes with backend settings.

Usage:
    from core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Processing request")
"""

from core.config import get_settings
from packages.logging import (
    setup_logging as _setup_logging,
    get_logger,
    ColoredFormatter,
)


def setup_logging() -> None:
    """Configure logging for the backend application using settings."""
    settings = get_settings()
    _setup_logging(
        log_level=settings.log_level,
        debug=settings.debug,
    )


# Initialize logging on module import
setup_logging()

__all__ = [
    "setup_logging",
    "get_logger",
    "ColoredFormatter",
]
