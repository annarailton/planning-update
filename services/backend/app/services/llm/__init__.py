"""Backend LLM Service.

Routes LLM requests to the appropriate provider package.

Features:
- Settings-based API key configuration
- System prompts from config
- Provider-specific routing
- Optional Langfuse tracing

Usage:
    from services.llm import LLMService

    llm = LLMService()

    # Use default provider (first available)
    response = await llm.chat(messages=[...])

    # Use specific provider
    response = await llm.chat(messages=[...], provider="anthropic")

    # Stream responses
    async for chunk in await llm.chat(messages=[...], stream=True):
        print(chunk)
"""

import json
import threading
from typing import AsyncGenerator

from core.config import get_settings
from core.logging import get_logger
from core.exceptions import ValidationError, ServiceUnavailableError
from config.prompts import get_system_prompt
from packages.langfuse import observe_llm
from packages.llm import LLMProvider, LLMResponse, ProviderInfo

logger = get_logger(__name__)

# Conditionally import LLM packages (only installed if feature is enabled)
openai_pkg = None
anthropic_pkg = None
gemini_pkg = None

try:
    import packages.openai as openai_pkg
except ImportError:
    logger.debug("OpenAI package not installed")

try:
    import packages.anthropic as anthropic_pkg
except ImportError:
    logger.debug("Anthropic package not installed")

try:
    import packages.gemini as gemini_pkg
except ImportError:
    logger.debug("Gemini package not installed")


__all__ = [
    "LLMService",
    "LLMProvider",
    "LLMResponse",
    "ProviderInfo",
    "get_llm_service",
    "reset_llm_service",
]


class LLMService:
    """Backend LLM service with multi-provider support.

    Provides a consistent interface for chat completions across
    OpenAI, Anthropic, and Gemini.

    All LLM calls are automatically traced via Langfuse when configured.
    """

    def __init__(self):
        """Initialize the LLM service with API keys from settings."""
        settings = get_settings()

        # Initialize clients if API keys are available AND package is installed
        self._openai_configured = False
        self._anthropic_configured = False
        self._gemini_configured = False

        if openai_pkg and settings.openai_api_key:
            openai_pkg.init_client(settings.openai_api_key)
            self._openai_configured = True
            logger.info("OpenAI provider initialized")

        if anthropic_pkg and settings.anthropic_api_key:
            anthropic_pkg.init_client(settings.anthropic_api_key)
            self._anthropic_configured = True
            logger.info("Anthropic provider initialized")

        if gemini_pkg and settings.gemini_api_key:
            gemini_pkg.init_client(settings.gemini_api_key)
            self._gemini_configured = True
            logger.info("Gemini provider initialized")

    @property
    def is_configured(self) -> bool:
        """Check if at least one provider is configured."""
        return (
            self._openai_configured
            or self._anthropic_configured
            or self._gemini_configured
        )

    def _get_default_provider(self) -> LLMProvider | None:
        """Get the default provider (first available)."""
        if self._openai_configured:
            return LLMProvider.OPENAI
        if self._anthropic_configured:
            return LLMProvider.ANTHROPIC
        if self._gemini_configured:
            return LLMProvider.GEMINI
        return None

    def get_available_providers(self) -> list[ProviderInfo]:
        """Get information about all providers and their availability."""
        providers = []

        # OpenAI
        if openai_pkg:
            providers.append(
                ProviderInfo(
                    provider=LLMProvider.OPENAI,
                    name="OpenAI",
                    available=self._openai_configured,
                    models=(
                        openai_pkg.get_model_ids() if self._openai_configured else []
                    ),
                    default_model=openai_pkg.DEFAULT_MODEL,
                )
            )
        else:
            providers.append(
                ProviderInfo(
                    provider=LLMProvider.OPENAI,
                    name="OpenAI",
                    available=False,
                    models=[],
                    default_model="gpt-5-mini",
                )
            )

        # Anthropic
        if anthropic_pkg:
            providers.append(
                ProviderInfo(
                    provider=LLMProvider.ANTHROPIC,
                    name="Anthropic",
                    available=self._anthropic_configured,
                    models=(
                        anthropic_pkg.get_model_ids()
                        if self._anthropic_configured
                        else []
                    ),
                    default_model=anthropic_pkg.DEFAULT_MODEL,
                )
            )
        else:
            providers.append(
                ProviderInfo(
                    provider=LLMProvider.ANTHROPIC,
                    name="Anthropic",
                    available=False,
                    models=[],
                    default_model="claude-sonnet-4-5-20250514",
                )
            )

        # Gemini
        if gemini_pkg:
            providers.append(
                ProviderInfo(
                    provider=LLMProvider.GEMINI,
                    name="Google Gemini",
                    available=self._gemini_configured,
                    models=(
                        gemini_pkg.get_model_ids() if self._gemini_configured else []
                    ),
                    default_model=gemini_pkg.DEFAULT_MODEL,
                )
            )
        else:
            providers.append(
                ProviderInfo(
                    provider=LLMProvider.GEMINI,
                    name="Google Gemini",
                    available=False,
                    models=[],
                    default_model="gemini-2.5-flash",
                )
            )

        return providers

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        provider: str | LLMProvider | None = None,
        stream: bool = False,
        system_prompt_key: str = "default",
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Chat with an LLM provider.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (provider-specific). Uses provider default if not specified.
            provider: Which provider to use (openai, anthropic, gemini). Uses default if not specified.
            stream: Whether to stream the response
            system_prompt_key: Key for system prompt from config (default: "default")
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse or async generator if streaming
        """
        # Validate messages
        if not messages:
            raise ValidationError("messages cannot be empty")

        # Resolve provider
        if provider is None:
            resolved_provider = self._get_default_provider()
            if not resolved_provider:
                raise ServiceUnavailableError(
                    "LLM",
                    "Set at least one of: OPENAI_API_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY",
                )
        elif isinstance(provider, str):
            try:
                resolved_provider = LLMProvider(provider.lower())
            except ValueError:
                raise ValidationError(
                    f"Invalid provider: {provider}. Must be one of: openai, anthropic, gemini"
                )
        else:
            resolved_provider = provider

        # Validate provider is configured
        if resolved_provider == LLMProvider.OPENAI and not self._openai_configured:
            raise ServiceUnavailableError("OpenAI", "Set OPENAI_API_KEY")
        if (
            resolved_provider == LLMProvider.ANTHROPIC
            and not self._anthropic_configured
        ):
            raise ServiceUnavailableError("Anthropic", "Set ANTHROPIC_API_KEY")
        if resolved_provider == LLMProvider.GEMINI and not self._gemini_configured:
            raise ServiceUnavailableError("Gemini", "Set GEMINI_API_KEY")

        # Get system prompt from backend config
        system_prompt = get_system_prompt(system_prompt_key)

        # Get default model if not specified
        if model is None:
            if resolved_provider == LLMProvider.OPENAI and openai_pkg:
                model = openai_pkg.DEFAULT_MODEL
            elif resolved_provider == LLMProvider.ANTHROPIC and anthropic_pkg:
                model = anthropic_pkg.DEFAULT_MODEL
            elif resolved_provider == LLMProvider.GEMINI and gemini_pkg:
                model = gemini_pkg.DEFAULT_MODEL
            else:
                # Fallback defaults if package not available (shouldn't happen)
                model = "gpt-5-mini"

        # Execute with tracing
        return await self._execute_chat(
            messages=messages,
            model=model,
            provider=resolved_provider,
            stream=stream,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    @observe_llm(name="chat")
    async def _execute_chat(
        self,
        messages: list[dict],
        model: str,
        provider: LLMProvider,
        stream: bool,
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
        **kwargs,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """Execute chat with automatic Langfuse tracing."""
        if stream:
            return self._stream_chat(
                messages=messages,
                model=model,
                provider=provider,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        # Non-streaming
        if provider == LLMProvider.OPENAI:
            if not openai_pkg:
                raise ServiceUnavailableError("OpenAI", "OpenAI package not installed")
            content = await openai_pkg.chat(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        elif provider == LLMProvider.ANTHROPIC:
            if not anthropic_pkg:
                raise ServiceUnavailableError(
                    "Anthropic", "Anthropic package not installed"
                )
            content = await anthropic_pkg.chat(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
        else:
            if not gemini_pkg:
                raise ServiceUnavailableError("Gemini", "Gemini package not installed")
            content = await gemini_pkg.chat(
                messages=messages,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

        return LLMResponse(
            content=content,
            model=model,
            provider=provider,
        )

    async def _stream_chat(
        self,
        messages: list[dict],
        model: str,
        provider: LLMProvider,
        system_prompt: str | None,
        temperature: float | None,
        max_tokens: int | None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream chat responses as SSE-formatted chunks."""
        # Emit start event
        yield f"data: {json.dumps({'type': 'start', 'model': model, 'provider': provider.value})}\n\n"

        try:
            if provider == LLMProvider.OPENAI:
                if not openai_pkg:
                    raise ServiceUnavailableError(
                        "OpenAI", "OpenAI package not installed"
                    )
                stream = openai_pkg.stream_chat(
                    messages=messages,
                    model=model,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            elif provider == LLMProvider.ANTHROPIC:
                if not anthropic_pkg:
                    raise ServiceUnavailableError(
                        "Anthropic", "Anthropic package not installed"
                    )
                stream = anthropic_pkg.stream_chat(
                    messages=messages,
                    model=model,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            else:
                if not gemini_pkg:
                    raise ServiceUnavailableError(
                        "Gemini", "Gemini package not installed"
                    )
                stream = gemini_pkg.stream_chat(
                    messages=messages,
                    model=model,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )

            async for chunk in stream:
                sse = {"choices": [{"delta": {"content": chunk}, "index": 0}]}
                yield f"data: {json.dumps(sse)}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {type(e).__name__}: {str(e)}")
            error_response = {
                "type": "error",
                "error": "Stream processing failed",
                "error_type": type(e).__name__,
            }
            yield f"data: {json.dumps(error_response)}\n\n"

    async def generate_text(
        self,
        prompt: str,
        model: str | None = None,
        provider: str | LLMProvider | None = None,
        **kwargs,
    ) -> str:
        """Generate text from a simple prompt.

        Args:
            prompt: The input prompt
            model: Model to use
            provider: Which provider to use
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        response = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            provider=provider,
            **kwargs,
        )
        return response.content

    async def stream_text(
        self,
        prompt: str,
        model: str | None = None,
        provider: str | LLMProvider | None = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream text generation.

        Args:
            prompt: The input prompt
            model: Model to use
            provider: Which provider to use
            **kwargs: Additional parameters

        Yields:
            SSE-formatted chunks
        """
        stream = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            provider=provider,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            yield chunk


# Singleton instance with thread-safe initialization

_service: LLMService | None = None
_service_lock = threading.Lock()


def get_llm_service() -> LLMService:
    """Get LLM service instance for dependency injection (thread-safe)."""
    global _service
    if _service is None:
        with _service_lock:
            # Double-check locking pattern
            if _service is None:
                _service = LLMService()
    return _service


def reset_llm_service() -> None:
    """Reset LLM service singleton (for testing)."""
    global _service
    with _service_lock:
        _service = None
