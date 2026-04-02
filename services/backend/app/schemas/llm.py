"""LLM API schemas.

Request and response schemas for the multi-provider LLM endpoints.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from .base import CamelCaseModel


class ChatMessage(BaseModel):
    """Chat message format."""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="Message role (system, user, assistant)"
    )
    content: str = Field(
        ..., min_length=1, max_length=100000, description="Message content"
    )


class ChatRequest(BaseModel):
    """Chat completion request."""

    messages: list[ChatMessage] = Field(
        ..., min_length=1, description="Conversation messages"
    )
    model: Optional[str] = Field(
        default=None, description="Model to use (provider-specific)"
    )
    provider: Optional[str] = Field(
        default=None,
        description="LLM provider (openai, anthropic, gemini). Uses default if not specified.",
    )
    stream: bool = Field(default=False, description="Stream the response")
    temperature: Optional[float] = Field(
        default=None, ge=0, le=2, description="Sampling temperature"
    )
    max_tokens: Optional[int] = Field(
        default=None, ge=1, le=200000, description="Max tokens to generate"
    )
    system_prompt_key: Optional[str] = Field(
        default="default", description="System prompt key from config"
    )


class GenerateRequest(BaseModel):
    """Simple text generation request."""

    prompt: str = Field(
        ..., min_length=1, max_length=100000, description="Input prompt"
    )
    model: Optional[str] = Field(default=None, description="Model to use")
    provider: Optional[str] = Field(default=None, description="LLM provider")
    stream: bool = Field(default=False, description="Stream the response")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=200000)


class CompletionResponse(CamelCaseModel):
    """Standard completion response."""

    content: str = Field(..., description="Generated content")
    model: str = Field(..., description="Model used")
    provider: str = Field(..., description="Provider used")
    usage: Optional[dict] = Field(default=None, description="Token usage stats")


class ProviderInfoResponse(CamelCaseModel):
    """Provider information."""

    provider: str
    name: str
    available: bool
    models: list[str]
    default_model: str


class ProvidersResponse(CamelCaseModel):
    """List of all providers."""

    providers: list[ProviderInfoResponse]
    default_provider: Optional[str] = None
