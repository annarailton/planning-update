"""Shared LLM types package.

Provides canonical type definitions for LLM operations shared
between backend and worker services.

Usage:
    from packages.llm import LLMProvider, LLMResponse, ProviderInfo

    # In service code
    response = LLMResponse(
        content="Hello!",
        model="gpt-4",
        provider=LLMProvider.OPENAI,
        usage={"prompt_tokens": 10, "completion_tokens": 20},
    )

    # Check provider
    if response.provider == LLMProvider.ANTHROPIC:
        ...
"""

from .types import (
    LLMProvider,
    LLMResponse,
    ProviderInfo,
)

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ProviderInfo",
]
