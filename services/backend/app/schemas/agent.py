"""Agent-related schemas."""

from typing import List, Optional
from pydantic import BaseModel, Field
from .llm import ChatMessage


class AgentChatRequest(BaseModel):
    """Agent chat request."""

    messages: List[ChatMessage] = Field(..., description="Conversation messages")
    stream: bool = Field(default=False, description="Stream the response")
    session_id: str = Field(..., description="Session ID")


class AgentCompletionResponse(BaseModel):
    """Agent completion response."""

    content: str = Field(..., description="Generated content")
    usage: Optional[dict] = Field(default=None, description="Token usage stats")
