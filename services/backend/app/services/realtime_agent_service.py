"""Realtime Agent Service

Uses OpenAI Agents SDK Realtime API for voice-enabled AI agents.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Iterable
from functools import partial

import httpx
from agents import function_tool
from agents.realtime import RealtimeAgent
from agents.realtime.model import RealtimeModelConfig
from agents.realtime.items import RealtimeItem
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions.memory import SQLAlchemySession

from core.config import get_settings
from core.logging import get_logger
from packages.db import fix_database_url_for_asyncpg

logger = get_logger(__name__)


# ============================================================================
# TOOLS - Define function tools for the realtime agents
# ============================================================================


@function_tool
async def get_weather(city: str) -> str:
    """
    Get the current weather for a city.

    Args:
        city: The name of the city to get weather for (e.g., "London", "New York", "Tokyo")
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Geocode the city name to get coordinates
            geo_response = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            geo_data = geo_response.json()

            if not geo_data.get("results"):
                return f"Sorry, I couldn't find the city '{city}'. Please try a different city name."

            location = geo_data["results"][0]
            lat, lon = location["latitude"], location["longitude"]
            city_name = location.get("name", city)
            country = location.get("country", "")

            # Get weather for coordinates
            weather_response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                },
            )
            current = weather_response.json().get("current", {})

            # Map weather codes to descriptions
            weather_descriptions = {
                0: "clear sky",
                1: "mainly clear",
                2: "partly cloudy",
                3: "overcast",
                45: "foggy",
                48: "depositing rime fog",
                51: "light drizzle",
                53: "moderate drizzle",
                55: "dense drizzle",
                61: "slight rain",
                63: "moderate rain",
                65: "heavy rain",
                71: "slight snow",
                73: "moderate snow",
                75: "heavy snow",
                80: "slight rain showers",
                81: "moderate rain showers",
                82: "violent rain showers",
                95: "thunderstorm",
                96: "thunderstorm with slight hail",
                99: "thunderstorm with heavy hail",
            }
            condition = weather_descriptions.get(
                current.get("weather_code", 0), "unknown conditions"
            )
            location_str = f"{city_name}, {country}" if country else city_name

            return (
                f"Current weather in {location_str}: {current.get('temperature_2m', 'N/A')}°F with {condition}. "
                f"Feels like {current.get('apparent_temperature', 'N/A')}°F. "
                f"Humidity is {current.get('relative_humidity_2m', 'N/A')}% and wind speed is {current.get('wind_speed_10m', 'N/A')} mph."
            )

    except httpx.TimeoutException:
        return "Sorry, the weather service is taking too long to respond. Please try again."
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return (
            f"Sorry, I couldn't fetch the weather for {city}. Please try again later."
        )


@function_tool
async def calculate(expression: str) -> str:
    """
    Calculate a mathematical expression.

    Args:
        expression: A mathematical expression to evaluate (e.g., "2 + 2", "10 * 5")
    """
    try:
        allowed_chars = set("0123456789+-*/.() ")
        if not all(c in allowed_chars for c in expression):
            return "Error: Invalid characters in expression. Only numbers and basic operators are allowed."
        result = eval(expression)
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating expression: {str(e)}"


@function_tool
async def get_current_time() -> str:
    """Get the current date and time."""
    now = datetime.now()
    return f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')}"


# ============================================================================
# AGENT CONFIGURATION
# ============================================================================


def create_realtime_agent() -> RealtimeAgent:
    """Create the realtime assistant agent."""
    return RealtimeAgent(
        name="Assistant",
        handoff_description="A helpful general assistant.",
        instructions=f"""{RECOMMENDED_PROMPT_PREFIX}
        You are a helpful AI assistant. You can help with general questions, get weather information,
        perform calculations, and tell the current time. Be friendly and conversational.
        
        If the user asks about something you cannot help with, let them know politely.
        """,
        tools=[get_weather, calculate, get_current_time],
    )


class RealtimeAgentService:
    """Service to manage realtime agent sessions."""

    def __init__(self):
        self.settings = get_settings()
        self.session_memory_db = None
        self._is_configured = bool(self.settings.openai_api_key)
        if self._is_configured:
            self._init_session_memory_db(
                session_memory_postgresdb_url=fix_database_url_for_asyncpg(
                    self.settings.database_url
                )
            )
            logger.info("Realtime Agent service initialized")
        else:
            logger.warning(
                "OpenAI API key not configured - Realtime Agent service disabled"
            )

    @property
    def is_configured(self) -> bool:
        return self._is_configured and self.session_memory_db is not None

    def _init_session_memory_db(
        self,
        session_memory_postgresdb_url: str,
    ) -> None:
        """Initialize the session memory database."""
        if not session_memory_postgresdb_url:
            raise ValueError("DATABASE_URL is required")
        try:
            self.session_memory_db = partial(
                SQLAlchemySession.from_url,
                url=session_memory_postgresdb_url,
                create_tables=True,
            )
            logger.info("Session memory database initialized for realtime agents")
        except Exception as e:
            logger.error(f"Failed to initialize session memory database: {e}")
            raise e

    def get_starting_agent(self) -> RealtimeAgent:
        return create_realtime_agent()

    def get_model_config(self) -> RealtimeModelConfig:
        return {
            "initial_model_settings": {
                "turn_detection": {
                    "type": "server_vad",
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                    "interrupt_response": True,
                    "create_response": True,
                },
            },
        }

    def sanitize_history_item(self, item: RealtimeItem) -> Dict[str, Any]:
        """Remove large binary payloads from history items."""
        item_dict = item.model_dump()
        content = item_dict.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") in {
                    "audio",
                    "input_audio",
                }:
                    part.pop("audio", None)
        return item_dict

    def _realtime_item_to_memory_item(
        self, item: RealtimeItem
    ) -> Dict[str, Any] | None:
        """Convert a realtime history item into a Responses API input item for storage."""
        if getattr(item, "type", None) != "message":
            return None

        role = getattr(item, "role", None)
        if role in {"user", "system"}:
            content: list[Dict[str, Any]] = []
            for part in getattr(item, "content", []) or []:
                part_type = getattr(part, "type", None)
                if part_type == "input_text":
                    text = getattr(part, "text", None)
                    if text:
                        content.append({"type": "input_text", "text": text})
                elif part_type == "input_audio":
                    transcript = getattr(part, "transcript", None)
                    if transcript:
                        content.append({"type": "input_text", "text": transcript})
                elif part_type == "input_image":
                    image_url = getattr(part, "image_url", None)
                    if image_url:
                        detail = getattr(part, "detail", None) or "auto"
                        content.append(
                            {
                                "type": "input_image",
                                "image_url": image_url,
                                "detail": detail,
                            }
                        )

            if not content:
                return None

            return {"type": "message", "role": role, "content": content}

        if role == "assistant":
            content: list[Dict[str, Any]] = []
            for part in getattr(item, "content", []) or []:
                part_type = getattr(part, "type", None)
                text = None
                if part_type == "text":
                    text = getattr(part, "text", None)
                elif part_type == "audio":
                    text = getattr(part, "transcript", None)
                if text:
                    content.append(
                        {"type": "output_text", "text": text, "annotations": []}
                    )

            if not content:
                return None

            status = getattr(item, "status", None) or "completed"
            return {
                "type": "message",
                "role": "assistant",
                "id": getattr(item, "item_id", ""),
                "status": status,
                "content": content,
            }

        return None

    async def store_history_items(
        self,
        session_id: str,
        items: Iterable[RealtimeItem],
    ) -> set[str]:
        """Persist new history items to the session memory store."""
        if not self.session_memory_db:
            return set()

        memory_items: list[Dict[str, Any]] = []
        stored_item_ids: set[str] = set()
        for item in items:
            item_id = getattr(item, "item_id", None)
            if not item_id:
                continue

            memory_item = self._realtime_item_to_memory_item(item)
            if memory_item is None:
                continue

            memory_items.append(memory_item)
            stored_item_ids.add(item_id)

        if not memory_items:
            return set()

        try:
            session = self.session_memory_db(session_id=session_id)
            await session.add_items(memory_items)
        except Exception as e:
            logger.error(f"Failed to store realtime session history: {e}")
            return set()
        return stored_item_ids


# Singleton
_service: Optional[RealtimeAgentService] = None


def get_realtime_agent_service() -> RealtimeAgentService:
    global _service
    if _service is None:
        _service = RealtimeAgentService()
    return _service
