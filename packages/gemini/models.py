"""Google Gemini Models Configuration.

Model registry for Google Gemini API.
Updated: January 2026
"""

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_TOKENS = 8192

MODELS = {
    # Gemini 3 Series (Preview)
    "gemini-3-flash-preview": {
        "name": "Gemini 3 Flash (Preview)",
        "description": "Latest preview model - fast and capable",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gemini-3-pro-preview": {
        "name": "Gemini 3 Pro (Preview)",
        "description": "Most capable preview model",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    # Gemini 2.5 Series (Stable)
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "description": "Fast and efficient for most tasks",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gemini-2.5-flash-lite": {
        "name": "Gemini 2.5 Flash Lite",
        "description": "Ultra-fast for simple tasks",
        "max_output_tokens": 4096,
        "supports_vision": True,
        "supports_tools": True,
    },
    # Gemini 2.0 Series
    "gemini-2.0-flash": {
        "name": "Gemini 2.0 Flash",
        "description": "Previous gen fast model",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gemini-2.0-flash-lite": {
        "name": "Gemini 2.0 Flash Lite",
        "description": "Previous gen lite model",
        "max_output_tokens": 4096,
        "supports_vision": True,
        "supports_tools": True,
    },
    # Gemini 1.5 Series (Legacy)
    "gemini-1.5-pro": {
        "name": "Gemini 1.5 Pro",
        "description": "Legacy pro model with long context",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gemini-1.5-flash": {
        "name": "Gemini 1.5 Flash",
        "description": "Legacy flash model",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
}

# Aliases for convenience
ALIASES = {
    "flash": "gemini-2.5-flash",
    "pro": "gemini-3-pro-preview",
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
