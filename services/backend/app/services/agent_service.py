"""Agent Service

Template is using openai agents sdk (but can be adapted on other frameworks too)

"""

import json
from typing import Any, AsyncGenerator, Dict, List, Union
from functools import partial

from agents import Agent, ModelSettings, Runner, trace
from agents.memory import SQLiteSession
from agents.extensions.memory import SQLAlchemySession
from services.agent_tools.tools import add, subtract, multiply, divide
from fastapi import Depends
from openai import AsyncOpenAI
from openai.types.responses import ResponseTextDeltaEvent
from core.config import Settings, get_settings
from core.logging import get_logger
from packages.db import fix_database_url_for_asyncpg
from config.prompts import get_agent_prompt

logger = get_logger(__name__)


class AgentService:
    """Service to invoke Agents"""

    def __init__(self):
        """Initialize the Agent service."""
        self.name = "mock agent"
        self.client = None
        self.main_agent = None
        self.session_memory_db = None
        settings = get_settings()
        if settings.openai_api_key:
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            logger.info(
                "OpenAI service initialized with Responses API for agent service"
            )
        else:
            logger.warning("OpenAI API key not configured")
        self._create_agent()
        self._init_session_memory_db(
            session_memory_postgresdb_url=fix_database_url_for_asyncpg(
                settings.database_url
            )
        )

    @property
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return (
            self._client is not None
            and self.main_agent is not None
            and self.session_memory_db is not None
        )

    def _init_session_memory_db(
        self,
        session_memory_postgresdb_url: str,
    ) -> SQLiteSession | SQLAlchemySession:
        """
        Initialize the session memory database.
        """
        if not session_memory_postgresdb_url:
            raise ValueError("DATABASE_URL is required")
        try:
            self.session_memory_db = partial(
                SQLAlchemySession.from_url,
                url=session_memory_postgresdb_url,
                create_tables=True,
            )
            logger.info("Session memory database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize session memory database: {e}")
            raise e

    def _create_agent(self) -> Agent:
        """
        Create an agent.
            This example demonstrates a flow for a agent that does math problems.

        """
        try:
            agent = Agent(
                name="Mock Agent",
                instructions=get_agent_prompt("mock_agent"),
                tools=[add, subtract, multiply, divide],
                model_settings=ModelSettings(tool_choice="required"),
            )
            self.main_agent = agent
            logger.info("Agent service initialized with mock agent")
        except Exception as e:
            logger.error(f"Failed to create agents: {e}")
            raise e

    async def invoke(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False,
        session_id: str = "test_session_id",
        **kwargs: Any,
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        Invoke an agent.

        Args:
            messages: List of message dicts with 'role' and 'content'
            stream: Whether to stream the response
            session_id: Session ID
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        """
        latest_user_msg = [msg for msg in messages if msg["role"] == "user"][-1]
        latest_user_msg = latest_user_msg["content"]
        if stream:
            return self._invoke_stream(latest_user_msg, session_id, **kwargs)
        else:
            return await self._invoke_text(latest_user_msg, session_id, **kwargs)

    async def _invoke_stream(
        self,
        latest_user_msg: str,
        session_id: str,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Invoke agent with streaming."""
        try:
            with trace(workflow_name=self.name, group_id=session_id):
                stream = Runner.run_streamed(
                    starting_agent=self.main_agent,
                    input=latest_user_msg,
                    session=self.session_memory_db(session_id=session_id),
                )
                async for event in stream.stream_events():
                    etype = getattr(event, "type", None)
                    if etype == "raw_response_event":
                        data = getattr(event, "data", None)
                        if isinstance(data, ResponseTextDeltaEvent):
                            delta = getattr(data, "delta", None)
                            if delta:
                                sse = {
                                    "choices": [
                                        {"delta": {"content": delta}, "index": 0}
                                    ]
                                }
                                yield f"data: {json.dumps(sse)}\n\n"

                    # (Optional) handle other stream events you care about:
                    # Completion lifecycle
                    elif etype in ("response.completed", "response.done"):
                        # Send DONE sentinel for frontend parsers
                        yield "data: [DONE]\n\n"
                        break

                # Safety: if we exited without a completed event, still close the stream
                yield "data: [DONE]\n\n"
        except Exception as e:
            # Send an error frame rather than silently dying
            logger.error(f"Streaming error: {str(e)}")
            error_data = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"

    async def _invoke_text(
        self,
        latest_user_msg: str,
        session_id: str,
        **kwargs: Any,
    ) -> str:
        """Invoke agent without streaming."""
        try:
            with trace(workflow_name=self.name, group_id=session_id):
                response = await Runner.run(
                    starting_agent=self.main_agent,
                    input=latest_user_msg,
                    session=self.session_memory_db(session_id=session_id),
                )
                return response.final_output
        except Exception as e:
            error_msg = f"Error invoking agent: {str(e)}"
            logger.error(error_msg)
            return error_msg


def get_agent_service(settings: Settings = Depends(get_settings)) -> AgentService:
    """Create Agent service instance with dependency injection.

    FastAPI will cache this per request, so we don't create multiple instances
    within the same request context.

    Args:
        settings: Application settings injected by FastAPI

    Returns:
        AgentService instance configured with current settings
    """
    return AgentService()
