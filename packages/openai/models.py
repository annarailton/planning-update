"""OpenAI Models Configuration.

Model registry for OpenAI Responses API.
Updated: January 2026
"""

DEFAULT_MODEL = "gpt-5-mini"

MODELS = {
    # GPT-5.2 Series (December 2025 - Latest)
    "gpt-5.2": {
        "name": "GPT-5.2",
        "description": "Most advanced frontier model for professional work and long-running agents",
        "max_output_tokens": 16384,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gpt-5.2-pro": {
        "name": "GPT-5.2 Pro",
        "description": "Extended reasoning for most complex professional tasks",
        "max_output_tokens": 32768,
        "supports_vision": True,
        "supports_tools": True,
    },
    # GPT-5 Series (August 2025)
    "gpt-5-mini": {
        "name": "GPT-5 Mini",
        "description": "Best general-purpose model with great price/performance",
        "max_output_tokens": 4096,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gpt-5-nano": {
        "name": "GPT-5 Nano",
        "description": "Ultra-low cost for classification and short replies",
        "max_output_tokens": 2048,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gpt-5": {
        "name": "GPT-5",
        "description": "Flagship model (use gpt-5.2 for latest)",
        "max_output_tokens": 8192,
        "supports_vision": True,
        "supports_tools": True,
    },
    # O-Series Reasoning Models
    "o4-mini": {
        "name": "O4 Mini",
        "description": "Cost-efficient deep reasoning for math/coding",
        "max_output_tokens": 4096,
        "supports_vision": True,
        "supports_tools": True,
    },
    "o3": {
        "name": "O3",
        "description": "Premium reasoning model for complex tasks",
        "max_output_tokens": 8192,
        "supports_vision": False,
        "supports_tools": True,
    },
    # GPT-4o Series (Legacy)
    "gpt-4o": {
        "name": "GPT-4o",
        "description": "Full-featured multimodal assistant",
        "max_output_tokens": 4096,
        "supports_vision": True,
        "supports_tools": True,
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "description": "Low-cost multimodal chat",
        "max_output_tokens": 4096,
        "supports_vision": True,
        "supports_tools": True,
    },
}


def get_model_ids() -> list[str]:
    """Get list of available model IDs."""
    return list(MODELS.keys())


def get_model_info(model_id: str) -> dict | None:
    """Get model info by ID."""
    return MODELS.get(model_id)


def get_default_max_tokens(model_id: str) -> int:
    """Get default max output tokens for a model."""
    model = MODELS.get(model_id)
    if model:
        return model.get("max_output_tokens", 4096)
    return 4096
