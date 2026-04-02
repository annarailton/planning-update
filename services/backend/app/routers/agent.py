"""Agents endpoints."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from core.dependencies import AgentServiceDep, AuthTokenDep
from core.logging import get_logger
from schemas.agent import AgentCompletionResponse, AgentChatRequest
from core.constants import StreamingHeaders
from utils import check_service_configured

logger = get_logger(__name__)

router = APIRouter(tags=["Agents"])


@router.post(
    "/invoke_agent",
    response_model=AgentCompletionResponse,
    summary="Invoke Agent",
)
async def invoke_agent(
    request: AgentChatRequest,
    service: AgentServiceDep,
    auth: AuthTokenDep,
) -> AgentCompletionResponse:
    """
    Invoke agent

    Supports:
    - Streaming responses via SSE

    """
    try:
        check_service_configured(
            service_name="Agent", is_configured=service.is_configured
        )

        logger.info("Chat request received for Agent")

        messages = [msg.model_dump() for msg in request.messages]

        if request.stream:

            async def generate():
                stream = await service.invoke(
                    messages=messages, stream=True, session_id=request.session_id
                )
                async for chunk in stream:
                    yield chunk

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers=StreamingHeaders.SSE_HEADERS,
            )
        else:
            result = await service.invoke(
                messages=messages, session_id=request.session_id
            )
            return AgentCompletionResponse(content=result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent invocation failed",
        )
