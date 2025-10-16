"""
WebSocket endpoints for OpenHands SDK.

These endpoints are separate from the main API routes to handle WebSocket-specific
authentication using query parameters instead of headers, since browsers cannot
send custom HTTP headers directly with WebSocket connections.
"""

import logging
from dataclasses import dataclass
from uuid import UUID

from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from openhands.agent_server.bash_service import BashEventService
from openhands.agent_server.config import get_default_config
from openhands.agent_server.conversation_service import ConversationService
from openhands.agent_server.dependencies import get_bash_event_service
from openhands.agent_server.models import BashEventBase
from openhands.agent_server.pub_sub import Subscriber
from openhands.sdk import Event, Message


# Backward-compat for tests that patch module variable
conversation_service: ConversationService | None = None


async def _resolve_conversation_service(
    svc: ConversationService = Depends(get_conversation_service),
) -> ConversationService:
    if conversation_service is not None:
        return conversation_service
    return svc


# Back-compat: allow calling events_socket directly in tests where FastAPI DI
# is not in effect. In such cases, the dependency parameter may be the Depends
# object itself; this helper normalizes it.
try:
    from fastapi.params import Depends as _DependsParam  # type: ignore
except Exception:  # pragma: no cover - fallback import structure
    _DependsParam = None  # type: ignore


sockets_router = APIRouter(prefix="/sockets", tags=["WebSockets"])
logger = logging.getLogger(__name__)


@sockets_router.websocket("/events/{conversation_id}")
async def events_socket(
    conversation_id: UUID,
    websocket: WebSocket,
    session_api_key: Annotated[str | None, Query(alias="session_api_key")] = None,
    resend_all: Annotated[bool, Query()] = False,
    conv_svc: ConversationService = Depends(_resolve_conversation_service),
):
    """WebSocket endpoint for conversation events."""
    # Perform authentication check before accepting the WebSocket connection
    config = get_default_config()
    if config.session_api_keys and session_api_key not in config.session_api_keys:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await websocket.accept()
    # Normalize dependency object when called directly (outside FastAPI DI)
    if _DependsParam is not None and isinstance(conv_svc, _DependsParam):
        conv_svc = conversation_service or ConversationService.get_instance(
            get_default_config()
        )
    event_service = await conv_svc.get_event_service(conversation_id)
    if event_service is None:
        await websocket.close(code=4004, reason="Conversation not found")
        return

    subscriber_id = await event_service.subscribe_to_events(
        _WebSocketSubscriber(websocket)
    )

    try:
        # Resend all existing events if requested
        if resend_all:
            page = await event_service.search_events(page_id=None)
            for event in page.items:
                await _send_event(event, websocket)

        # Listen for messages over the socket
        while True:
            try:
                data = await websocket.receive_json()
                message = Message.model_validate(data)
                await event_service.send_message(message, True)
            except WebSocketDisconnect:
                return
            except Exception as e:
                logger.exception("error_in_subscription", stack_info=True)
                if isinstance(e, (RuntimeError, ConnectionError)):
                    raise
    finally:
        await event_service.unsubscribe_from_events(subscriber_id)


@sockets_router.websocket("/bash-events")
async def bash_events_socket(
    websocket: WebSocket,
    session_api_key: Annotated[str | None, Query(alias="session_api_key")] = None,
    resend_all: Annotated[bool, Query()] = False,
    bash_event_service: BashEventService = Depends(get_bash_event_service),
):
    """WebSocket endpoint for bash events."""
    config = get_default_config()
    if config.session_api_keys and session_api_key not in config.session_api_keys:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    await websocket.accept()
    subscriber_id = await bash_event_service.subscribe_to_events(
        _BashWebSocketSubscriber(websocket)
    )
    try:
        # Resend all existing events if requested
        if resend_all:
            page = await bash_event_service.search_bash_events(page_id=None)
            for event in page.items:
                await _send_bash_event(event, websocket)

        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                return
            except Exception as e:
                logger.exception("error_in_bash_event_subscription", stack_info=True)
                if isinstance(e, (RuntimeError, ConnectionError)):
                    raise
    finally:
        await bash_event_service.unsubscribe_from_events(subscriber_id)


async def _send_event(event: Event, websocket: WebSocket):
    try:
        dumped = event.model_dump()
        await websocket.send_json(dumped)
    except Exception:
        logger.exception("error_sending_event:{event}", stack_info=True)


@dataclass
class _WebSocketSubscriber(Subscriber):
    """WebSocket subscriber for conversation events."""

    websocket: WebSocket

    async def __call__(self, event: Event):
        await _send_event(event, self.websocket)


async def _send_bash_event(event: BashEventBase, websocket: WebSocket):
    try:
        dumped = event.model_dump()
        await websocket.send_json(dumped)
    except Exception:
        logger.exception("error_sending_event:{event}", stack_info=True)


@dataclass
class _BashWebSocketSubscriber(Subscriber[BashEventBase]):
    """WebSocket subscriber for bash events."""

    websocket: WebSocket

    async def __call__(self, event: BashEventBase):
        await _send_bash_event(event, self.websocket)
