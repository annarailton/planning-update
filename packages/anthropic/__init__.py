"""Anthropic SDK Wrapper.

Thin wrapper around AsyncAnthropic with retry logic.

Usage:
    import packages.anthropic as anthropic

    # Simple chat
    response = await anthropic.chat([{"role": "user", "content": "Hello"}])

    # With system prompt
    response = await anthropic.chat(
        [{"role": "user", "content": "Hello"}],
        system_prompt="You are a helpful assistant."
    )

    # Streaming
    async for chunk in anthropic.stream_chat([{"role": "user", "content": "Hello"}]):
        print(chunk, end="")

    # Direct client access for advanced use
    client = anthropic.get_client()
    response = await client.messages.create(...)
"""

import logging
import os
import threading
from typing import AsyncGenerator

from anthropic import AsyncAnthropic, APIConnectionError, APITimeoutError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .models import (
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
    MODELS,
    ALIASES,
    resolve_model,
    get_model_ids,
    get_model_info,
    get_default_max_tokens,
)

__all__ = [
    "chat",
    "stream_chat",
    "get_client",
    "init_client",
    "is_configured",
    "DEFAULT_MODEL",
    "DEFAULT_MAX_TOKENS",
    "MODELS",
    "ALIASES",
    "resolve_model",
    "get_model_ids",
    "get_model_info",
    "get_default_max_tokens",
]

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None
_client_lock = threading.Lock()


def get_client() -> AsyncAnthropic:
    """Get the Anthropic client singleton (thread-safe).

    Raises:
        RuntimeError: If client not initialized and no ANTHROPIC_API_KEY env var.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    raise RuntimeError(
                        "Anthropic client not initialized. Call init_client(api_key) or set ANTHROPIC_API_KEY."
                    )
                _client = AsyncAnthropic(api_key=api_key)
    return _client


def init_client(api_key: str) -> AsyncAnthropic:
    """Initialize the Anthropic client with an API key (thread-safe).

    Args:
        api_key: Anthropic API key

    Returns:
        The initialized AsyncAnthropic client
    """
    global _client
    with _client_lock:
        _client = AsyncAnthropic(api_key=api_key)
        logger.info("Anthropic client initialized")
    return _client


def is_configured() -> bool:
    """Check if Anthropic is configured (has API key)."""
    if _client is not None:
        return True
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _format_messages(
    messages: list[dict],
    system_prompt: str | None = None,
) -> tuple[str | None, list[dict]]:
    """Format messages for Anthropic API.

    Anthropic requires system prompt to be separate from messages.

    Returns:
        Tuple of (system_prompt, formatted_messages)
    """
    system = system_prompt
    formatted = []

    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            if system:
                system = f"{system}\n\n{content}"
            else:
                system = content
        else:
            role = "assistant" if msg.get("role") == "assistant" else "user"
            formatted.append({"role": role, "content": msg.get("content", "")})

    return system, formatted


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
        model: Model ID or alias (default: claude-sonnet-4-5)
        max_tokens: Maximum output tokens (default: 4096)
        temperature: Sampling temperature
        system_prompt: System prompt (separate from messages for Anthropic)
        **kwargs: Additional params passed to the API

    Returns:
        The response text content
    """
    client = get_client()

    resolved_model = resolve_model(model)
    system, formatted_messages = _format_messages(messages, system_prompt)

    params = {
        "model": resolved_model,
        "messages": formatted_messages,
        "max_tokens": max_tokens or get_default_max_tokens(resolved_model),
    }

    if system:
        params["system"] = system
    if temperature is not None:
        params["temperature"] = temperature

    params.update(kwargs)

    response = await client.messages.create(**params)
    return response.content[0].text if response.content else ""


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
        model: Model ID or alias (default: claude-sonnet-4-5)
        max_tokens: Maximum output tokens (default: 4096)
        temperature: Sampling temperature
        system_prompt: System prompt (separate from messages for Anthropic)
        **kwargs: Additional params passed to the API

    Yields:
        Text chunks as they arrive
    """
    client = get_client()

    resolved_model = resolve_model(model)
    system, formatted_messages = _format_messages(messages, system_prompt)

    params = {
        "model": resolved_model,
        "messages": formatted_messages,
        "max_tokens": max_tokens or get_default_max_tokens(resolved_model),
    }

    if system:
        params["system"] = system
    if temperature is not None:
        params["temperature"] = temperature

    params.update(kwargs)

    async with client.messages.stream(**params) as stream:
        async for text in stream.text_stream:
            yield text
