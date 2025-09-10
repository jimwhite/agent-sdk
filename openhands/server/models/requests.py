"""Request models for the OpenHands Agent SDK API."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


try:
    from openhands.sdk.llm.message import Message  # type: ignore
except ImportError:
    # Mock Message class for testing
    class Message(BaseModel):  # type: ignore
        """Mock Message class for testing."""

        role: str
        content: List[Dict[str, Any]]


class AgentConfig(BaseModel):
    """Configuration for creating an Agent."""

    llm_config: Dict[str, Any] = Field(
        description="LLM configuration dictionary from LLM.model_dump()",
        examples=[
            {
                "model": "claude-sonnet-4-20250514",
                "api_key": "your-api-key",
                "base_url": "https://api.anthropic.com",
            }
        ],
    )
    tools: List[str] = Field(
        default_factory=list,
        description="List of tool names to enable",
        examples=[["bash", "file_editor"]],
    )
    workdir: Optional[str] = Field(
        default=None,
        description="Working directory for the conversation",
        examples=["/tmp/workspace"],
    )


class CreateConversationRequest(BaseModel):
    """Request model for creating a new conversation.

    Maps to Conversation.__init__() parameters.
    """

    agent_config: AgentConfig = Field(..., description="Configuration for the agent")
    max_iteration_per_run: int = Field(
        default=500, description="Maximum iterations per run", ge=1, le=10000
    )
    visualize: bool = Field(default=True, description="Whether to enable visualization")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_config": {
                    "llm_config": {
                        "model": "claude-sonnet-4-20250514",
                        "api_key": "your-api-key",
                    },
                    "tools": ["bash", "file_editor"],
                    "workdir": "/tmp/workspace",
                },
                "max_iteration_per_run": 500,
                "visualize": True,
            }
        }


class SendMessageRequest(BaseModel):
    """Request model for sending a message to a conversation.

    Maps to Conversation.send_message() parameters.
    """

    message: Message = Field(..., description="Message to send to the agent")

    class Config:
        json_schema_extra = {
            "example": {
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello! Please help me with a task."}
                    ],
                }
            }
        }


class SetConfirmationModeRequest(BaseModel):
    """Request model for setting confirmation mode.

    Maps to Conversation.set_confirmation_mode() parameters.
    """

    enabled: bool = Field(..., description="Whether to enable confirmation mode")

    class Config:
        json_schema_extra = {"example": {"enabled": True}}


class RejectPendingActionsRequest(BaseModel):
    """Request model for rejecting pending actions.

    Maps to Conversation.reject_pending_actions() parameters.
    """

    reason: str = Field(
        default="User rejected the action",
        description="Reason for rejecting the actions",
    )

    class Config:
        json_schema_extra = {
            "example": {"reason": "The proposed action is not what I wanted"}
        }
