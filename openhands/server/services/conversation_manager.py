"""Conversation management service for the OpenHands Agent SDK server."""

import os
import tempfile
from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.llm import LLM
from openhands.server.models.requests import AgentConfig, CreateConversationRequest
from openhands.server.models.responses import (
    ConversationResponse,
    ConversationStateResponse,
)
from openhands.tools import BashTool, FileEditorTool


class ConversationManager:
    """Manages conversation lifecycle and state."""

    def __init__(self):
        self._conversations: Dict[str, Any] = {}
        self._agent_configs: Dict[str, AgentConfig] = {}
        self._created_at: Dict[str, datetime] = {}
        self._workdirs: Dict[str, str] = {}

    async def create_conversation(
        self, request: CreateConversationRequest
    ) -> ConversationResponse:
        """Create new conversation from request.

        Args:
            request: Conversation creation request

        Returns:
            ConversationResponse with created conversation info

        Raises:
            HTTPException: If conversation creation fails
        """
        try:
            # Create LLM from config
            llm = LLM(**request.agent_config.llm_config)

            # Set up working directory
            workdir = request.agent_config.workdir
            if not workdir:
                workdir = tempfile.mkdtemp(prefix="openhands_conv_")
            elif not os.path.exists(workdir):
                os.makedirs(workdir, exist_ok=True)

            # Create tools based on configuration
            tools = []
            for tool_name in request.agent_config.tools:
                if tool_name == "bash":
                    tools.append(BashTool.create(working_dir=workdir))
                elif tool_name == "file_editor":
                    tools.append(FileEditorTool.create())
                else:
                    # Log warning for unknown tools but don't fail
                    print(f"Warning: Unknown tool '{tool_name}' requested")

            # Create agent
            agent = Agent(llm=llm, tools=tools)

            # Create conversation
            conversation = Conversation(
                agent=agent,
                max_iteration_per_run=request.max_iteration_per_run,
                visualize=request.visualize,
            )

            # Store conversation and metadata
            created_at = datetime.now()
            self._conversations[conversation.id] = conversation
            self._agent_configs[conversation.id] = request.agent_config
            self._created_at[conversation.id] = created_at
            self._workdirs[conversation.id] = workdir

            return ConversationResponse.from_conversation(
                conversation,
                request.agent_config,
                created_at,
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create conversation: {str(e)}"
            )

    async def get_conversation(self, conversation_id: str) -> Any:
        """Get conversation by ID.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation instance

        Raises:
            HTTPException: If conversation not found
        """
        if conversation_id not in self._conversations:
            raise HTTPException(
                status_code=404, detail=f"Conversation {conversation_id} not found"
            )
        return self._conversations[conversation_id]

    async def get_conversation_info(self, conversation_id: str) -> ConversationResponse:
        """Get conversation info for response.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            ConversationResponse with conversation info
        """
        conversation = await self.get_conversation(conversation_id)
        agent_config = self._agent_configs[conversation_id]
        created_at = self._created_at[conversation_id]

        return ConversationResponse.from_conversation(
            conversation, agent_config, created_at
        )

    async def get_conversation_state(
        self, conversation_id: str
    ) -> ConversationStateResponse:
        """Get conversation state.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            ConversationStateResponse with full state
        """
        conversation = await self.get_conversation(conversation_id)
        return ConversationStateResponse.from_state(conversation.state)

    async def list_conversations(self) -> List[ConversationResponse]:
        """List all conversations.

        Returns:
            List of ConversationResponse objects
        """
        result = []
        for conv_id, conversation in self._conversations.items():
            agent_config = self._agent_configs[conv_id]
            created_at = self._created_at[conv_id]
            result.append(
                ConversationResponse.from_conversation(
                    conversation, agent_config, created_at
                )
            )
        return result

    async def delete_conversation(self, conversation_id: str) -> None:
        """Delete conversation and clean up resources.

        Args:
            conversation_id: Unique conversation identifier

        Raises:
            HTTPException: If conversation not found
        """
        if conversation_id not in self._conversations:
            raise HTTPException(
                status_code=404, detail=f"Conversation {conversation_id} not found"
            )

        # Clean up working directory if it was created by us
        workdir = self._workdirs.get(conversation_id)
        if workdir and workdir.startswith(tempfile.gettempdir()):
            try:
                import shutil

                shutil.rmtree(workdir, ignore_errors=True)
            except Exception as e:
                print(f"Warning: Failed to clean up workdir {workdir}: {e}")

        # Remove from all tracking dictionaries
        del self._conversations[conversation_id]
        del self._agent_configs[conversation_id]
        del self._created_at[conversation_id]
        del self._workdirs[conversation_id]

    def get_stats(self) -> Dict[str, int]:
        """Get manager statistics.

        Returns:
            Dictionary with manager statistics
        """
        return {
            "total_conversations": len(self._conversations),
            "active_conversations": len(
                [c for c in self._conversations.values() if not c.state.agent_finished]
            ),
            "finished_conversations": len(
                [c for c in self._conversations.values() if c.state.agent_finished]
            ),
        }
