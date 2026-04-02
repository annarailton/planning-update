"""Langfuse client singleton management.

Provides thread-safe lazy initialization of the Langfuse client.
Reads configuration directly from environment variables.
"""

import logging
import os
import threading
from functools import lru_cache
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Environment variable names
LANGFUSE_PUBLIC_KEY_ENV = "LANGFUSE_PUBLIC_KEY"
LANGFUSE_SECRET_KEY_ENV = "LANGFUSE_SECRET_KEY"
LANGFUSE_HOST_ENV = "LANGFUSE_HOST"
LANGFUSE_HOST_DEFAULT = "https://cloud.langfuse.com"

# Thread-safe singleton state
_langfuse_observe: Optional[Callable] = None
_langfuse_client: Optional[Any] = None
_client_lock = threading.Lock()


@lru_cache(maxsize=1)
def is_langfuse_enabled() -> bool:
    """Check if Langfuse is configured (cached, thread-safe).

    Returns True if both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
    environment variables are set.
    """
    public_key = os.getenv(LANGFUSE_PUBLIC_KEY_ENV)
    secret_key = os.getenv(LANGFUSE_SECRET_KEY_ENV)
    return bool(public_key and secret_key)


def get_langfuse_host() -> str:
    """Get Langfuse host URL from environment."""
    return os.getenv(LANGFUSE_HOST_ENV, LANGFUSE_HOST_DEFAULT)


def get_langfuse_client() -> Optional[Any]:
    """Get singleton Langfuse client (lazy initialization, thread-safe).

    Returns None if Langfuse is not configured or if initialization fails.
    """
    global _langfuse_client
    if _langfuse_client is None and is_langfuse_enabled():
        with _client_lock:
            # Double-check after acquiring lock
            if _langfuse_client is None:
                try:
                    from langfuse import Langfuse

                    _langfuse_client = Langfuse()
                except Exception as e:
                    logger.debug(f"Failed to initialize Langfuse client: {e}")
    return _langfuse_client


def get_observe_decorator() -> Optional[Callable]:
    """Get the Langfuse observe decorator (lazy loaded, thread-safe).

    Returns None if Langfuse is not configured or not installed.
    """
    global _langfuse_observe
    if _langfuse_observe is None and is_langfuse_enabled():
        with _client_lock:
            # Double-check after acquiring lock
            if _langfuse_observe is None:
                try:
                    from langfuse import observe as lf_observe

                    _langfuse_observe = lf_observe
                except ImportError:
                    pass
    return _langfuse_observe


def flush() -> None:
    """Flush pending traces to Langfuse.

    Safe to call even if Langfuse is not configured.
    """
    langfuse = get_langfuse_client()
    if langfuse:
        try:
            langfuse.flush()
        except Exception as e:
            logger.debug(f"Failed to flush Langfuse: {e}")


def log_status(logger_instance: Optional[logging.Logger] = None) -> None:
    """Log Langfuse configuration status at startup.

    Args:
        logger_instance: Optional logger to use. Defaults to module logger.
    """
    log = logger_instance or logger
    if is_langfuse_enabled():
        log.info(f"Langfuse enabled - host: {get_langfuse_host()}")
    else:
        log.debug("Langfuse not configured - tracing disabled")
