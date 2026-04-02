"""Feature flags endpoint for frontend consumption."""

from fastapi import APIRouter

from core.config import get_settings

router = APIRouter(tags=["features"])


def _is_temporal_available() -> bool:
    """Check if Temporal is truly available (package installed + configured)."""
    try:
        from packages.temporal import is_temporal_enabled

        return is_temporal_enabled()
    except ImportError:
        return False


@router.get("/features")
async def get_features() -> dict:
    """
    Get enabled feature flags.

    Returns feature flags for frontend to conditionally render UI elements.
    Structure matches features.json categories:
    - infrastructure: redis, worker, temporal
    - llm: openai, anthropic, gemini
    - integrations: langfuse
    """
    settings = get_settings()

    return {
        "infrastructure": {
            "redis": settings.is_redis_enabled,
            "worker": settings.is_worker_enabled,
            "temporal": _is_temporal_available(),
        },
        "llm": {
            "openai": settings.feature_llm_openai and bool(settings.openai_api_key),
            "anthropic": settings.feature_llm_anthropic
            and bool(settings.anthropic_api_key),
            "gemini": settings.feature_llm_gemini and bool(settings.gemini_api_key),
        },
        "integrations": {
            "langfuse": settings.is_langfuse_enabled,
        },
    }
