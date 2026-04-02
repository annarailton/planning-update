"""Multi-Provider LLM endpoints.

Provides a unified API for interacting with multiple LLM providers
(OpenAI, Anthropic, Gemini) through a single interface.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.dependencies import AuthTokenDep, LLMServiceDep
from core.constants import StreamingHeaders
from core.logging import get_logger
from core.exceptions import ValidationError
from services.llm import LLMProvider
from schemas.llm import (
    ChatRequest,
    GenerateRequest,
    CompletionResponse,
    ProviderInfoResponse,
    ProvidersResponse,
)

logger = get_logger("llm_router")

router = APIRouter(tags=["LLM"])


def _parse_provider(provider_str: str | None) -> LLMProvider | None:
    """Parse provider string to enum."""
    if not provider_str:
        return None
    try:
        return LLMProvider(provider_str.lower())
    except ValueError:
        raise ValidationError(
            f"Invalid provider: {provider_str}. Must be one of: openai, anthropic, gemini"
        )


@router.get(
    "/providers", response_model=ProvidersResponse, summary="List Available Providers"
)
async def list_providers(service: LLMServiceDep, auth: AuthTokenDep):
    """Get list of all LLM providers and their availability.

    Returns information about which providers are configured and their available models.
    """
    providers_info = service.get_available_providers()

    # Find default provider
    default_provider = None
    for p in providers_info:
        if p.available:
            default_provider = p.provider.value
            break

    return ProvidersResponse(
        providers=[
            ProviderInfoResponse(
                provider=p.provider.value,
                name=p.name,
                available=p.available,
                models=p.models,
                default_model=p.default_model,
            )
            for p in providers_info
        ],
        default_provider=default_provider,
    )


@router.post("/chat", response_model=CompletionResponse, summary="Chat Completion")
async def chat(request: ChatRequest, service: LLMServiceDep, auth: AuthTokenDep):
    """Chat completion with conversation history.

    Supports multiple providers (OpenAI, Anthropic, Gemini) through a unified interface.
    If no provider is specified, uses the first available one.
    """
    provider = _parse_provider(request.provider)
    messages = [msg.model_dump() for msg in request.messages]

    if request.stream:

        async def generate():
            stream = await service.chat(
                messages=messages,
                model=request.model,
                provider=provider,
                stream=True,
                system_prompt_key=request.system_prompt_key or "default",
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            async for chunk in stream:
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers=StreamingHeaders.SSE_HEADERS,
        )
    else:
        result = await service.chat(
            messages=messages,
            model=request.model,
            provider=provider,
            system_prompt_key=request.system_prompt_key or "default",
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return CompletionResponse(
            content=result.content,
            model=result.model,
            provider=result.provider.value,
            usage=result.usage,
        )


@router.post(
    "/generate", response_model=CompletionResponse, summary="Simple Text Generation"
)
async def generate(
    request: GenerateRequest, service: LLMServiceDep, auth: AuthTokenDep
):
    """Simple text generation from a single prompt (no conversation history)."""
    provider = _parse_provider(request.provider)

    if request.stream:

        async def generate_stream():
            async for chunk in service.stream_text(
                prompt=request.prompt,
                model=request.model,
                provider=provider,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                yield chunk

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers=StreamingHeaders.SSE_HEADERS,
        )
    else:
        result = await service.chat(
            messages=[{"role": "user", "content": request.prompt}],
            model=request.model,
            provider=provider,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return CompletionResponse(
            content=result.content,
            model=result.model,
            provider=result.provider.value,
            usage=result.usage,
        )
