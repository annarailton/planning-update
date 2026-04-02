"""OpenAI SDK Wrapper.

Thin wrapper around AsyncOpenAI with retry logic.
Uses the Responses API by default.

Usage:
    import packages.openai as openai

    # Simple chat
    response = await openai.chat([{"role": "user", "content": "Hello"}])

    # Streaming
    async for chunk in openai.stream_chat([{"role": "user", "content": "Hello"}]):
        print(chunk, end="")

    # Direct client access for advanced use
    client = openai.get_client()
    response = await client.responses.create(...)
"""

import logging
import os
import threading
from typing import AsyncGenerator

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import APIConnectionError, APITimeoutError, RateLimitError

from .models import DEFAULT_MODEL, MODELS, get_model_ids, get_model_info, get_default_max_tokens

__all__ = [
    "chat",
    "stream_chat",
    "get_client",
    "init_client",
    "is_configured",
    "DEFAULT_MODEL",
    "MODELS",
    "get_model_ids",
    "get_model_info",
    "get_default_max_tokens",
]

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None
_client_lock = threading.Lock()


def get_client() -> AsyncOpenAI:
    """Get the OpenAI client singleton (thread-safe).

    Raises:
        RuntimeError: If client not initialized and no OPENAI_API_KEY env var.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise RuntimeError(
                        "OpenAI client not initialized. Call init_client(api_key) or set OPENAI_API_KEY."
                    )
                _client = AsyncOpenAI(api_key=api_key)
    return _client


def init_client(api_key: str) -> AsyncOpenAI:
    """Initialize the OpenAI client with an API key (thread-safe).

    Args:
        api_key: OpenAI API key

    Returns:
        The initialized AsyncOpenAI client
    """
    global _client
    with _client_lock:
        _client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")
    return _client


def is_configured() -> bool:
    """Check if OpenAI is configured (has API key)."""
    if _client is not None:
        return True
    return bool(os.environ.get("OPENAI_API_KEY"))


@retry(
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int | None = None,
    temperature: float | None = None,
    system_prompt: str | None = None,
    **kwargs,
) -> str:
    """Send a chat request and return the response text.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model ID (default: gpt-5-mini)
        max_tokens: Maximum output tokens (uses model default if not specified)
        temperature: Sampling temperature
        system_prompt: Optional system prompt to prepend
        **kwargs: Additional params passed to the API

    Returns:
        The response text content
    """
    client = get_client()

    # Prepend system prompt if provided
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    params = {
        "model": model,
        "input": messages,
    }

    if max_tokens is not None:
        params["max_output_tokens"] = max_tokens
    elif model in MODELS:
        params["max_output_tokens"] = MODELS[model].get("max_output_tokens", 4096)

    if temperature is not None:
        params["temperature"] = temperature

    params.update(kwargs)

    response = await client.responses.create(**params)
    return response.output_text


@retry(
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError, RateLimitError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
)
async def stream_chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int | None = None,
    temperature: float | None = None,
    system_prompt: str | None = None,
    **kwargs,
) -> AsyncGenerator[str, None]:
    """Stream a chat response, yielding text chunks.

    Args:
        messages: List of message dicts with 'role' and 'content'
        model: Model ID (default: gpt-5-mini)
        max_tokens: Maximum output tokens
        temperature: Sampling temperature
        system_prompt: Optional system prompt to prepend
        **kwargs: Additional params passed to the API

    Yields:
        Text chunks as they arrive
    """
    client = get_client()

    # Prepend system prompt if provided
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    params = {
        "model": model,
        "input": messages,
        "stream": True,
    }

    if max_tokens is not None:
        params["max_output_tokens"] = max_tokens
    elif model in MODELS:
        params["max_output_tokens"] = MODELS[model].get("max_output_tokens", 4096)

    if temperature is not None:
        params["temperature"] = temperature

    params.update(kwargs)

    stream = await client.responses.create(**params)

    async for event in stream:
        event_type = getattr(event, "type", None)

        if event_type == "response.output_text.delta":
            delta = getattr(event, "delta", None)
            if delta:
                yield delta

        elif event_type in ("response.completed", "response.done"):
            return

        elif event_type in ("response.error", "response.failed"):
            error_msg = getattr(getattr(event, "error", None), "message", "Unknown error")
            raise RuntimeError(f"OpenAI streaming error: {error_msg}")
