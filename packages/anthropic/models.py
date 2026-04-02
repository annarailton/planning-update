"""Anthropic Models Configuration.

Model registry for Anthropic Claude API.
Updated: January 2026
"""

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_MAX_TOKENS = 4096

MODELS = {
    # Claude 4.5 Series (Latest)
    "claude-sonnet-4-5-20250929": {
        "name": "Claude Sonnet 4.5",
        "description": "Latest balanced model - excellent reasoning and speed",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    "claude-opus-4-5-20251124": {
        "name": "Claude Opus 4.5",
        "description": "Most capable model for complex tasks",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    # Claude 4 Series
    "claude-sonnet-4-20250514": {
        "name": "Claude Sonnet 4",
        "description": "Balanced performance and cost",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    "claude-opus-4-20250514": {
        "name": "Claude Opus 4",
        "description": "Premium model for complex tasks",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    # Claude 3.5 Series
    "claude-3-5-haiku-20241022": {
        "name": "Claude 3.5 Haiku",
        "description": "Fast and cost-effective for simple tasks",
        "max_output_tokens": 4096,
        "supports_vision": True,
        "supports_tools": True,
    },
}

# Aliases for convenience
ALIASES = {
    "claude-sonnet-4-5": "claude-sonnet-4-5-20250929",
    "claude-opus-4-5": "claude-opus-4-5-20251124",
    "claude-sonnet-4": "claude-sonnet-4-20250514",
    "claude-opus-4": "claude-opus-4-20250514",
    "claude-3-5-haiku": "claude-3-5-haiku-20241022",
    # Common shortcuts
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251124",
    "haiku": "claude-3-5-haiku-20241022",
}


def resolve_model(model_id: str) -> str:
    """Resolve model alias to full model ID."""
    return ALIASES.get(model_id, model_id)


def get_model_ids() -> list[str]:
    """Get list of available model IDs."""
    return list(MODELS.keys())


def get_model_info(model_id: str) -> dict | None:
    """Get model info by ID (resolves aliases)."""
    resolved = resolve_model(model_id)
    return MODELS.get(resolved)


def get_default_max_tokens(model_id: str) -> int:
    """Get default max output tokens for a model."""
    resolved = resolve_model(model_id)
    model = MODELS.get(resolved)
    if model:
        return model.get("max_output_tokens", DEFAULT_MAX_TOKENS)
    return DEFAULT_MAX_TOKENS
