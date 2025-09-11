"""Response models for the OpenHands Agent SDK API."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from openhands.sdk.conversation.conversation import Conversation
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
