"""Shared LLM types used across backend and worker services.

This module defines the canonical types for LLM operations to prevent
drift between services. Always import from here, not from service-level code.
"""

from dataclasses import dataclass, field
from enum import Enum


class LLMProvider(str, Enum):
    """Available LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"


@dataclass
class LLMResponse:
    """Standardized response from any provider."""

    content: str
    model: str
    provider: LLMProvider
    usage: dict | None = None  # Token usage stats (if available)


@dataclass
class ProviderInfo:
    """Information about a provider."""

    provider: LLMProvider
    name: str
    available: bool
    models: list[str] = field(default_factory=list)
    default_model: str = ""
