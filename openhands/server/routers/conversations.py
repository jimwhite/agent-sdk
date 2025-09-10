"""Conversation API router with 1-1 mapping to Conversation class methods."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..models.requests import (
    CreateConversationRequest,
    RejectPendingActionsRequest,
    SendMessageRequest,
    SetConfirmationModeRequest,
)
from ..models.responses import (
    ConversationResponse,
    ConversationStateResponse,
    StatusResponse,
)
from ..services.conversation_manager import ConversationManager


router = APIRouter()

# Global conversation manager instance (will be injected via dependency)
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """FastAPI dependency to get conversation manager."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    request: CreateConversationRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> ConversationResponse:
    """Create new conversation.

    Maps to: Conversation.__init__(agent, callbacks, max_iteration_per_run, visualize)

    Args:
        request: Conversation creation request
        manager: Conversation manager dependency

    Returns:
        ConversationResponse with created conversation info
    """
    return await manager.create_conversation(request)


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    manager: ConversationManager = Depends(get_conversation_manager),
) -> List[ConversationResponse]:
    """List all conversations.

    Returns:
        List of all active conversations
    """
    return await manager.list_conversations()


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> ConversationResponse:
    """Get conversation info.

    Maps to: conversation.id property access

    Args:
        conversation_id: Unique conversation identifier
        manager: Conversation manager dependency

    Returns:
        ConversationResponse with conversation info
    """
    return await manager.get_conversation_info(conversation_id)


@router.delete("/{conversation_id}", response_model=StatusResponse)
async def delete_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> StatusResponse:
    """Delete conversation.

    Args:
        conversation_id: Unique conversation identifier
        manager: Conversation manager dependency

    Returns:
        StatusResponse confirming deletion
    """
    await manager.delete_conversation(conversation_id)
    return StatusResponse(
        status="deleted", message=f"Conversation {conversation_id} deleted successfully"
    )


@router.post("/{conversation_id}/send_message", response_model=StatusResponse)
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> StatusResponse:
    """Send message to conversation.

    Maps to: conversation.send_message(message)

    Args:
        conversation_id: Unique conversation identifier
        request: Message sending request
        manager: Conversation manager dependency

    Returns:
        StatusResponse confirming message was sent
    """
    conversation = await manager.get_conversation(conversation_id)

    try:
        conversation.send_message(request.message)
        return StatusResponse(
            status="message_sent", message="Message sent successfully to conversation"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to send message: {str(e)}")


@router.post("/{conversation_id}/run", response_model=StatusResponse)
async def run_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> StatusResponse:
    """Run conversation.

    Maps to: conversation.run()

    Args:
        conversation_id: Unique conversation identifier
        manager: Conversation manager dependency

    Returns:
        StatusResponse confirming run completion
    """
    conversation = await manager.get_conversation(conversation_id)

    try:
        conversation.run()
        return StatusResponse(
            status="run_completed", message="Conversation run completed successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to run conversation: {str(e)}"
        )


@router.post("/{conversation_id}/set_confirmation_mode", response_model=StatusResponse)
async def set_confirmation_mode(
    conversation_id: str,
    request: SetConfirmationModeRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> StatusResponse:
    """Set confirmation mode.

    Maps to: conversation.set_confirmation_mode(enabled)

    Args:
        conversation_id: Unique conversation identifier
        request: Confirmation mode setting request
        manager: Conversation manager dependency

    Returns:
        StatusResponse confirming mode change
    """
    conversation = await manager.get_conversation(conversation_id)

    try:
        conversation.set_confirmation_mode(request.enabled)
        return StatusResponse(
            status="confirmation_mode_set",
            message=f"Confirmation mode {'enabled' if request.enabled else 'disabled'}",
            data={"enabled": request.enabled},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to set confirmation mode: {str(e)}"
        )


@router.post("/{conversation_id}/reject_pending_actions", response_model=StatusResponse)
async def reject_pending_actions(
    conversation_id: str,
    request: RejectPendingActionsRequest,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> StatusResponse:
    """Reject pending actions.

    Maps to: conversation.reject_pending_actions(reason)

    Args:
        conversation_id: Unique conversation identifier
        request: Action rejection request
        manager: Conversation manager dependency

    Returns:
        StatusResponse confirming actions were rejected
    """
    conversation = await manager.get_conversation(conversation_id)

    try:
        conversation.reject_pending_actions(request.reason)
        return StatusResponse(
            status="actions_rejected",
            message="Pending actions rejected successfully",
            data={"reason": request.reason},
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reject pending actions: {str(e)}"
        )


@router.post("/{conversation_id}/pause", response_model=StatusResponse)
async def pause_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> StatusResponse:
    """Pause conversation.

    Maps to: conversation.pause()

    Args:
        conversation_id: Unique conversation identifier
        manager: Conversation manager dependency

    Returns:
        StatusResponse confirming pause
    """
    conversation = await manager.get_conversation(conversation_id)

    try:
        conversation.pause()
        return StatusResponse(
            status="paused", message="Conversation paused successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to pause conversation: {str(e)}"
        )


@router.get("/{conversation_id}/events", response_model=List[Dict[str, Any]])
async def get_events(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> List[Dict[str, Any]]:
    """Get conversation events.

    Maps to: conversation.state.events

    Args:
        conversation_id: Unique conversation identifier
        manager: Conversation manager dependency

    Returns:
        List of serialized events
    """
    conversation = await manager.get_conversation(conversation_id)
    return [event.model_dump() for event in conversation.state.events]


@router.get("/{conversation_id}/state", response_model=ConversationStateResponse)
async def get_state(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager),
) -> ConversationStateResponse:
    """Get conversation state.

    Maps to: conversation.state

    Args:
        conversation_id: Unique conversation identifier
        manager: Conversation manager dependency

    Returns:
        ConversationStateResponse with full state
    """
    return await manager.get_conversation_state(conversation_id)
