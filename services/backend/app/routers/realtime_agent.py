"""Realtime Agent WebSocket endpoints."""

import asyncio
import base64
import json
import struct
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from agents.realtime import RealtimeRunner, RealtimeSession, RealtimeSessionEvent
from core.logging import get_logger
from services.realtime_agent_service import (
    get_realtime_agent_service,
    RealtimeAgentService,
)

logger = get_logger(__name__)
router = APIRouter(tags=["Realtime Agents"])


class RealtimeWebSocketManager:
    """Manages WebSocket connections for realtime agent sessions."""

    def __init__(self):
        self.active_sessions: Dict[str, RealtimeSession] = {}
        self.session_contexts: Dict[str, Any] = {}
        self.websockets: Dict[str, WebSocket] = {}
        self.event_tasks: Dict[str, asyncio.Task] = {}
        self.history_cache: Dict[str, Dict[str, Any]] = {}
        self.history_sequence: Dict[str, list[str]] = {}
        self.last_history_lengths: Dict[str, int] = {}
        self.last_stored_item_ids: Dict[str, Optional[str]] = {}
        self.storage_queues: Dict[str, asyncio.Queue[list[Any]]] = {}
        self.storage_tasks: Dict[str, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, session_id: str) -> bool:
        service = get_realtime_agent_service()

        if not service.is_configured:
            await websocket.close(
                code=4000, reason="Realtime agent service not configured"
            )
            return False

        await websocket.accept()
        self.websockets[session_id] = websocket

        try:
            agent = service.get_starting_agent()
            runner = RealtimeRunner(agent)
            session_context = await runner.run(model_config=service.get_model_config())
            session = await session_context.__aenter__()

            self.active_sessions[session_id] = session
            self.session_contexts[session_id] = session_context
            self.event_tasks[session_id] = asyncio.create_task(
                self._process_events(session_id)
            )
            self.history_cache[session_id] = {}
            self.history_sequence[session_id] = []
            self.last_history_lengths[session_id] = 0
            self.last_stored_item_ids[session_id] = None
            self.storage_queues[session_id] = asyncio.Queue(maxsize=50)
            self.storage_tasks[session_id] = asyncio.create_task(
                self._persist_history(session_id)
            )

            logger.info(f"Realtime session {session_id} connected")
            return True

        except Exception as e:
            logger.error(f"Failed to create realtime session: {e}")
            await websocket.close(code=4001, reason=str(e))
            return False

    async def disconnect(self, session_id: str):
        if session_id in self.event_tasks:
            self.event_tasks[session_id].cancel()
            try:
                await self.event_tasks[session_id]
            except asyncio.CancelledError:
                pass
            del self.event_tasks[session_id]

        if session_id in self.storage_tasks:
            self.storage_tasks[session_id].cancel()
            try:
                await self.storage_tasks[session_id]
            except asyncio.CancelledError:
                pass
            del self.storage_tasks[session_id]

        if session_id in self.session_contexts:
            try:
                await self.session_contexts[session_id].__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing session context: {e}")
            del self.session_contexts[session_id]

        self.active_sessions.pop(session_id, None)
        self.websockets.pop(session_id, None)
        self.history_cache.pop(session_id, None)
        self.history_sequence.pop(session_id, None)
        self.last_history_lengths.pop(session_id, None)
        self.last_stored_item_ids.pop(session_id, None)
        self.storage_queues.pop(session_id, None)
        logger.info(f"Realtime session {session_id} disconnected")

    def _order_history_items(self, history: list[Any]) -> list[Any]:
        """Order history items using previous_item_id while preserving original order."""
        if not history:
            return []

        id_to_item: Dict[str, Any] = {}
        adjacency: Dict[str, list[str]] = {}
        roots: list[str] = []

        for item in history:
            item_id = getattr(item, "item_id", None)
            if not item_id:
                continue
            id_to_item[item_id] = item
            adjacency.setdefault(item_id, [])

        for item in history:
            item_id = getattr(item, "item_id", None)
            prev_id = getattr(item, "previous_item_id", None)
            if not item_id:
                continue
            if prev_id and prev_id in id_to_item:
                adjacency.setdefault(prev_id, []).append(item_id)
            else:
                roots.append(item_id)

        ordered: list[Any] = []
        visited: set[str] = set()

        def _walk(start_id: str) -> None:
            current_id = start_id
            while current_id and current_id not in visited:
                visited.add(current_id)
                ordered.append(id_to_item[current_id])
                next_ids = adjacency.get(current_id, [])
                if not next_ids:
                    break
                next_id = next_ids[0]
                for sibling_id in next_ids[1:]:
                    if sibling_id not in visited:
                        roots.append(sibling_id)
                current_id = next_id

        for root_id in roots:
            if root_id not in visited:
                _walk(root_id)

        if len(ordered) < len(history):
            ordered_ids = {getattr(item, "item_id", None) for item in ordered}
            for item in history:
                item_id = getattr(item, "item_id", None)
                if not item_id or item_id not in ordered_ids:
                    ordered.append(item)

        return ordered

    def _merge_history_items(self, session_id: str, items: list[Any]) -> list[Any]:
        cache = self.history_cache.setdefault(session_id, {})
        sequence = self.history_sequence.setdefault(session_id, [])

        for item in items:
            item_id = getattr(item, "item_id", None)
            if not item_id:
                continue
            cache[item_id] = item
            if item_id not in sequence:
                sequence.append(item_id)

        ordered_items = [cache[item_id] for item_id in sequence if item_id in cache]
        return self._order_history_items(ordered_items)

    def _get_ordered_history_for_event(
        self, session_id: str, event: RealtimeSessionEvent
    ) -> list[Any]:
        if event.type == "history_added":
            return self._merge_history_items(session_id, [event.item])
        if event.type == "history_updated":
            return self._merge_history_items(session_id, event.history)
        return []

    def _advance_ready_items(
        self,
        ordered_history: list[Any],
        last_stored_item_id: Optional[str],
        service: RealtimeAgentService,
    ) -> tuple[list[Any], Optional[str]]:
        start_index = 0
        if last_stored_item_id:
            for idx, item in enumerate(ordered_history):
                if getattr(item, "item_id", None) == last_stored_item_id:
                    start_index = idx + 1
                    break

        ready_items: list[Any] = []
        new_last_stored_item_id = last_stored_item_id
        for item in ordered_history[start_index:]:
            item_id = getattr(item, "item_id", None)
            item_type = getattr(item, "type", None)
            if item_type == "function_call":
                if item_id:
                    new_last_stored_item_id = item_id
                continue

            if service._realtime_item_to_memory_item(item) is None:
                break
            ready_items.append(item)
            if item_id:
                new_last_stored_item_id = item_id

        return ready_items, new_last_stored_item_id

    async def _process_events(self, session_id: str):
        try:
            session = self.active_sessions[session_id]
            websocket = self.websockets[session_id]
            service = get_realtime_agent_service()
            last_history_len = self.last_history_lengths.get(session_id, 0)
            storage_queue = self.storage_queues.setdefault(
                session_id, asyncio.Queue(maxsize=50)
            )
            last_stored_item_id = self.last_stored_item_ids.get(session_id)

            async for event in session:
                if event.type == "history_updated":
                    history_len = len(event.history)
                    if history_len > last_history_len:
                        last_history_len = history_len

                ordered_history = self._get_ordered_history_for_event(session_id, event)
                if ordered_history:
                    ready_items, last_stored_item_id = self._advance_ready_items(
                        ordered_history,
                        last_stored_item_id,
                        service,
                    )
                    if ready_items:
                        try:
                            storage_queue.put_nowait(ready_items)
                        except asyncio.QueueFull:
                            logger.warning(
                                "Realtime storage queue full; deferring history persistence"
                            )
                    self.last_history_lengths[session_id] = last_history_len
                    self.last_stored_item_ids[session_id] = last_stored_item_id

                event_data = self._serialize_event(event, service)
                await websocket.send_text(json.dumps(event_data))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error processing events for session {session_id}: {e}")

    async def _persist_history(self, session_id: str):
        try:
            service = get_realtime_agent_service()
            storage_queue = self.storage_queues.setdefault(
                session_id, asyncio.Queue(maxsize=50)
            )

            while True:
                items = await storage_queue.get()
                await service.store_history_items(
                    session_id=session_id,
                    items=items,
                )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(
                f"Realtime history persistence error for session {session_id}: {e}"
            )

    def _serialize_event(
        self, event: RealtimeSessionEvent, service: RealtimeAgentService
    ) -> Dict[str, Any]:
        base: Dict[str, Any] = {"type": event.type}

        if event.type == "agent_start":
            base["agent"] = event.agent.name
        elif event.type == "agent_end":
            base["agent"] = event.agent.name
        elif event.type == "handoff":
            base["from"] = event.from_agent.name
            base["to"] = event.to_agent.name
        elif event.type == "tool_start":
            base["tool"] = event.tool.name
        elif event.type == "tool_end":
            base["tool"] = event.tool.name
            base["output"] = str(event.output)
        elif event.type == "audio":
            base["audio"] = base64.b64encode(event.audio.data).decode("utf-8")
        elif event.type == "history_updated":
            base["history"] = [
                service.sanitize_history_item(item) for item in event.history
            ]
        elif event.type == "history_added":
            try:
                base["item"] = service.sanitize_history_item(event.item)
            except Exception:
                base["item"] = None
        elif event.type == "error":
            base["error"] = str(getattr(event, "error", "Unknown error"))

        return base


manager = RealtimeWebSocketManager()


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for realtime agent sessions."""
    if not await manager.connect(websocket, session_id):
        return

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "audio":
                int16_data = message["data"]
                audio_bytes = struct.pack(f"{len(int16_data)}h", *int16_data)
                session = manager.active_sessions.get(session_id)
                if session:
                    await session.send_audio(audio_bytes)

            elif msg_type == "text":
                text = message.get("text", "").strip()
                if text:
                    session = manager.active_sessions.get(session_id)
                    if session:
                        await session.send_message(
                            {
                                "type": "message",
                                "role": "user",
                                "content": [{"type": "input_text", "text": text}],
                            }
                        )

            elif msg_type == "interrupt":
                session = manager.active_sessions.get(session_id)
                if session:
                    await session.interrupt()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        await manager.disconnect(session_id)


@router.get("/status", summary="Check Realtime Agent Status")
async def get_realtime_status():
    """Check if the realtime agent service is configured and ready."""
    service = get_realtime_agent_service()
    return {
        "configured": service.is_configured,
        "active_sessions": len(manager.active_sessions),
    }
