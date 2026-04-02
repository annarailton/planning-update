"""Worker LLM Service.

Simplified LLM interface for background jobs.
Uses the provider-specific packages directly.

Usage:
    from services.llm import LLMService, LLMProvider

    llm = get_llm_service()

    # Use default provider
    response = await llm.chat(messages=[...])

    # Generate text
    text = await llm.generate_text("Summarize this document...")
"""

import threading

from core.config import get_settings
from packages.exceptions import ValidationError, ServiceUnavailableError
from packages.logging import get_logger
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
    """Worker LLM service for background job processing.

    Simplified interface focused on non-streaming completions.
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
        return self._openai_configured or self._anthropic_configured or self._gemini_configured

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
            providers.append(ProviderInfo(
                provider=LLMProvider.OPENAI,
                name="OpenAI",
                available=self._openai_configured,
                models=openai_pkg.get_model_ids() if self._openai_configured else [],
                default_model=openai_pkg.DEFAULT_MODEL,
            ))
        else:
            providers.append(ProviderInfo(
                provider=LLMProvider.OPENAI,
                name="OpenAI",
                available=False,
                models=[],
                default_model="gpt-5-mini",
            ))

        # Anthropic
        if anthropic_pkg:
            providers.append(ProviderInfo(
                provider=LLMProvider.ANTHROPIC,
                name="Anthropic",
                available=self._anthropic_configured,
                models=anthropic_pkg.get_model_ids() if self._anthropic_configured else [],
                default_model=anthropic_pkg.DEFAULT_MODEL,
            ))
        else:
            providers.append(ProviderInfo(
                provider=LLMProvider.ANTHROPIC,
                name="Anthropic",
                available=False,
                models=[],
                default_model="claude-sonnet-4-5-20250514",
            ))

        # Gemini
        if gemini_pkg:
            providers.append(ProviderInfo(
                provider=LLMProvider.GEMINI,
                name="Google Gemini",
                available=self._gemini_configured,
                models=gemini_pkg.get_model_ids() if self._gemini_configured else [],
                default_model=gemini_pkg.DEFAULT_MODEL,
            ))
        else:
            providers.append(ProviderInfo(
                provider=LLMProvider.GEMINI,
                name="Google Gemini",
                available=False,
                models=[],
                default_model="gemini-2.5-flash",
            ))

        return providers

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        provider: str | LLMProvider | None = None,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> LLMResponse:
        """Chat with an LLM provider.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use. Uses provider default if not specified.
            provider: Which provider to use. Uses default if not specified.
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated content
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
        if resolved_provider == LLMProvider.ANTHROPIC and not self._anthropic_configured:
            raise ServiceUnavailableError("Anthropic", "Set ANTHROPIC_API_KEY")
        if resolved_provider == LLMProvider.GEMINI and not self._gemini_configured:
            raise ServiceUnavailableError("Gemini", "Set GEMINI_API_KEY")

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

        # Call the appropriate provider
        if resolved_provider == LLMProvider.OPENAI:
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
        elif resolved_provider == LLMProvider.ANTHROPIC:
            if not anthropic_pkg:
                raise ServiceUnavailableError("Anthropic", "Anthropic package not installed")
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
            provider=resolved_provider,
        )

    async def generate_text(
        self,
        prompt: str,
        model: str | None = None,
        provider: str | LLMProvider | None = None,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str:
        """Generate text from a simple prompt.

        Args:
            prompt: The input prompt
            model: Model to use
            provider: Which provider to use
            system_prompt: Optional system prompt
            **kwargs: Additional parameters

        Returns:
            Generated text
        """
        response = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            provider=provider,
            system_prompt=system_prompt,
            **kwargs,
        )
        return response.content


# Singleton service instance with thread-safe initialization
_llm_service: LLMService | None = None
_llm_service_lock = threading.Lock()


def get_llm_service() -> LLMService:
    """Get LLM service singleton (thread-safe)."""
    global _llm_service
    if _llm_service is None:
        with _llm_service_lock:
            # Double-check locking pattern
            if _llm_service is None:
                _llm_service = LLMService()
    return _llm_service


def reset_llm_service() -> None:
    """Reset LLM service singleton (for testing)."""
    global _llm_service
    with _llm_service_lock:
        _llm_service = None
