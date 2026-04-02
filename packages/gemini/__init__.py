"""Google Gemini SDK Wrapper.

Thin wrapper around google-genai with retry logic.

Usage:
    import packages.gemini as gemini

    # Simple chat
    response = await gemini.chat([{"role": "user", "content": "Hello"}])

    # With system prompt
    response = await gemini.chat(
        [{"role": "user", "content": "Hello"}],
        system_prompt="You are a helpful assistant."
    )

    # Streaming
    async for chunk in gemini.stream_chat([{"role": "user", "content": "Hello"}]):
        print(chunk, end="")

    # Direct client access for advanced use
    client = gemini.get_client()
    response = await client.aio.models.generate_content(...)
"""

import logging
import os
import threading
from typing import AsyncGenerator

from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.api_core.exceptions import ServiceUnavailable, ResourceExhausted, DeadlineExceeded

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

_client: genai.Client | None = None
_client_lock = threading.Lock()


def get_client() -> genai.Client:
    """Get the Gemini client singleton (thread-safe).

    Raises:
        RuntimeError: If client not initialized and no GEMINI_API_KEY env var.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
                if not api_key:
                    raise RuntimeError(
                        "Gemini client not initialized. Call init_client(api_key) or set GEMINI_API_KEY."
                    )
                _client = genai.Client(api_key=api_key)
    return _client


def init_client(api_key: str) -> genai.Client:
    """Initialize the Gemini client with an API key (thread-safe).

    Args:
        api_key: Google/Gemini API key

    Returns:
        The initialized genai.Client
    """
    global _client
    with _client_lock:
        _client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialized")
    return _client


def is_configured() -> bool:
    """Check if Gemini is configured (has API key)."""
    if _client is not None:
        return True
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


def _format_messages(
    messages: list[dict],
    system_prompt: str | None = None,
) -> tuple[str | None, list[types.Content]]:
    """Format messages for Gemini API.

    Returns:
        Tuple of (system_instruction, contents)
    """
    system = system_prompt
    contents = []

    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            if system:
                system = f"{system}\n\n{content}"
            else:
                system = content
        else:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg.get("content", ""))])
            )

    return system, contents


@retry(
    retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted, DeadlineExceeded)),
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
        model: Model ID or alias (default: gemini-2.5-flash)
        max_tokens: Maximum output tokens
        temperature: Sampling temperature
        system_prompt: System instruction
        **kwargs: Additional params passed to the API

    Returns:
        The response text content
    """
    client = get_client()

    resolved_model = resolve_model(model)
    system_instruction, contents = _format_messages(messages, system_prompt)

    generation_config = {}
    if max_tokens is not None:
        generation_config["max_output_tokens"] = max_tokens
    elif resolved_model in MODELS:
        generation_config["max_output_tokens"] = MODELS[resolved_model].get(
            "max_output_tokens", DEFAULT_MAX_TOKENS
        )

    if temperature is not None:
        generation_config["temperature"] = temperature

    generation_config.update(kwargs)

    config = None
    if system_instruction or generation_config:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            **generation_config,
        )

    response = await client.aio.models.generate_content(
        model=resolved_model,
        contents=contents,
        config=config,
    )

    if response.candidates and response.candidates[0].content.parts:
        return response.candidates[0].content.parts[0].text
    return ""


@retry(
    retry=retry_if_exception_type((ServiceUnavailable, ResourceExhausted, DeadlineExceeded)),
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
        model: Model ID or alias (default: gemini-2.5-flash)
        max_tokens: Maximum output tokens
        temperature: Sampling temperature
        system_prompt: System instruction
        **kwargs: Additional params passed to the API

    Yields:
        Text chunks as they arrive
    """
    client = get_client()

    resolved_model = resolve_model(model)
    system_instruction, contents = _format_messages(messages, system_prompt)

    generation_config = {}
    if max_tokens is not None:
        generation_config["max_output_tokens"] = max_tokens
    elif resolved_model in MODELS:
        generation_config["max_output_tokens"] = MODELS[resolved_model].get(
            "max_output_tokens", DEFAULT_MAX_TOKENS
        )

    if temperature is not None:
        generation_config["temperature"] = temperature

    generation_config.update(kwargs)

    config = None
    if system_instruction or generation_config:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            **generation_config,
        )

    async for chunk in client.aio.models.generate_content_stream(
        model=resolved_model,
        contents=contents,
        config=config,
    ):
        if chunk.candidates and chunk.candidates[0].content.parts:
            text = chunk.candidates[0].content.parts[0].text
            if text:
                yield text
