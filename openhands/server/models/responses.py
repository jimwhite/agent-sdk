"""Response models for the OpenHands Agent SDK API."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from openhands.sdk.conversation.conversation import Conversation
from openhands.sdk.conversation.state import ConversationState
from openhands.server.models.requests import AgentConfig


class StatusResponse(BaseModel):
    """Generic status response for operations."""

    status: str = Field(..., description="Status of the operation")
    message: Optional[str] = Field(
        default=None, description="Additional message about the operation"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional data from the operation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
            }
        }


class ConversationResponse(BaseModel):
    """Response model for conversation information."""

    id: str = Field(..., description="Unique conversation identifier")
    agent_config: AgentConfig = Field(
        ..., description="Agent configuration used for this conversation"
    )
    max_iteration_per_run: int = Field(..., description="Maximum iterations per run")
    visualize: bool = Field(..., description="Whether visualization is enabled")
    created_at: str = Field(
        ..., description="ISO timestamp when conversation was created"
    )

    @classmethod
    def from_conversation(
        cls,
        conversation: Conversation,
        agent_config: AgentConfig,
        created_at: Optional[datetime] = None,
    ) -> "ConversationResponse":
        """Create response from Conversation instance."""
        return cls(
            id=conversation.id,
            agent_config=agent_config,
            max_iteration_per_run=conversation.max_iteration_per_run,
            visualize=conversation._visualizer is not None,
            created_at=(created_at or datetime.now()).isoformat(),
        )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "conv_123e4567-e89b-12d3-a456-426614174000",
                "agent_config": {
                    "llm_config": {
                        "model": "claude-sonnet-4-20250514",
                        "api_key": "***",
                    },
                    "tools": ["bash", "file_editor"],
                    "workdir": "/tmp/workspace",
                },
                "max_iteration_per_run": 500,
                "visualize": True,
                "created_at": "2024-01-01T12:00:00",
            }
        }


class ConversationStateResponse(BaseModel):
    """Response model for conversation state.

    Maps directly to ConversationState properties.
    """

    id: str = Field(..., description="Conversation state identifier")
    events: List[Dict[str, Any]] = Field(
        ..., description="List of all events in the conversation"
    )
    agent_finished: bool = Field(
        ..., description="Whether the agent has finished processing"
    )
    confirmation_mode: bool = Field(
        ..., description="Whether confirmation mode is enabled"
    )
    agent_waiting_for_confirmation: bool = Field(
        ..., description="Whether agent is waiting for user confirmation"
    )
    agent_paused: bool = Field(..., description="Whether agent execution is paused")
    activated_knowledge_microagents: List[str] = Field(
        ..., description="List of activated knowledge microagents"
    )

    @classmethod
    def from_state(cls, state: ConversationState) -> "ConversationStateResponse":
        """Create response from ConversationState instance."""
        return cls(
            id=state.id,
            events=[event.model_dump() for event in state.events],
            agent_finished=state.agent_finished,
            confirmation_mode=state.confirmation_mode,
            agent_waiting_for_confirmation=state.agent_waiting_for_confirmation,
            agent_paused=state.agent_paused,
            activated_knowledge_microagents=state.activated_knowledge_microagents,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "conv_123e4567-e89b-12d3-a456-426614174000",
                "events": [
                    {
                        "id": "event_1",
                        "timestamp": "2024-01-01T12:00:00",
                        "type": "MessageEvent",
                        "source": "user",
                    }
                ],
                "agent_finished": False,
                "confirmation_mode": False,
                "agent_waiting_for_confirmation": False,
                "agent_paused": False,
                "activated_knowledge_microagents": [],
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional error details"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ConversationNotFound",
                "message": "Conversation with ID 'invalid-id' not found",
                "details": {"conversation_id": "invalid-id"},
            }
        }
