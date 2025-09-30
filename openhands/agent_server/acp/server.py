"""Agent Client Protocol (ACP) server implementation."""

import asyncio
import os
from typing import Any
from uuid import UUID

from openhands.agent_server.conversation_service import ConversationService
from openhands.agent_server.models import StartConversationRequest
from openhands.sdk import Message, TextContent as SDKTextContent
from openhands.sdk.llm import LLM
from openhands.tools.preset.default import get_default_agent

from .models import (
    AuthenticateRequest,
    AuthenticateResponse,
    ContentBlock,
    FileSystemCapabilities,
    InitializeRequest,
    InitializeResponse,
    NewSessionRequest,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    ServerCapabilities,
    SessionCancelNotification,
    TextContent,
)
from .transport import JSONRPCTransport


class ACPServer:
    """Agent Client Protocol server for OpenHands."""

    def __init__(self, conversation_service: ConversationService) -> None:
        """Initialize the ACP server."""
        self.conversation_service = conversation_service
        self.transport = JSONRPCTransport()
        self.sessions: dict[str, UUID] = {}  # session_id -> conversation_id
        self.initialized = False

        # Register ACP method handlers
        self.transport.register_handler("initialize", self._handle_initialize)
        self.transport.register_handler("authenticate", self._handle_authenticate)
        self.transport.register_handler("session/new", self._handle_session_new)
        self.transport.register_handler("session/prompt", self._handle_session_prompt)
        self.transport.register_handler("session/cancel", self._handle_session_cancel)

    def _handle_initialize(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle initialize request."""
        try:
            InitializeRequest.model_validate(params)
        except Exception as e:
            raise ValueError(f"Invalid initialize request: {e}")

        # For now, we support basic capabilities
        server_capabilities = ServerCapabilities(
            fs=FileSystemCapabilities(readTextFile=True, writeTextFile=True),
            terminal=True,
        )

        response = InitializeResponse(
            protocolVersion="1.0.0", serverCapabilities=server_capabilities
        )

        self.initialized = True
        return response.model_dump()

    def _handle_authenticate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle authenticate request."""
        # For now, we don't require authentication
        AuthenticateRequest.model_validate(params)
        response = AuthenticateResponse(success=True)
        return response.model_dump()

    def _handle_session_new(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle session/new request."""
        if not self.initialized:
            raise RuntimeError("Server not initialized")

        request = NewSessionRequest.model_validate(params)

        # Create a new conversation
        working_dir = request.workingDirectory or os.getcwd()

        # Create a default agent for the conversation
        # In a real implementation, this would be configurable
        llm = LLM(model="gpt-4o-mini", service_id="acp-agent")
        agent = get_default_agent(llm=llm, cli_mode=True)

        create_request = StartConversationRequest(agent=agent, working_dir=working_dir)

        # Run async method in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            conversation_info = loop.run_until_complete(
                self.conversation_service.start_conversation(create_request)
            )
        finally:
            loop.close()

        # Store session mapping
        session_id = f"session-{conversation_info.id}"
        self.sessions[session_id] = conversation_info.id

        response = NewSessionResponse(sessionId=session_id)
        return response.model_dump()

    def _handle_session_prompt(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle session/prompt request."""
        if not self.initialized:
            raise RuntimeError("Server not initialized")

        request = PromptRequest.model_validate(params)

        # Check if session exists
        if request.sessionId not in self.sessions:
            raise ValueError(f"Unknown session: {request.sessionId}")

        conversation_id = self.sessions[request.sessionId]

        # Convert prompt content to message text
        message_parts = []
        for content in request.prompt:
            if content.type == "text":
                message_parts.append(content.text)
            elif content.type == "resource":
                message_parts.append(f"[Resource: {content.uri}]")

        message_text = "\n".join(message_parts)

        # Create SDK message
        message = Message(role="user", content=[SDKTextContent(text=message_text)])

        # Send message to conversation using async methods
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Get event service and send message
            event_service = loop.run_until_complete(
                self.conversation_service.get_event_service(conversation_id)
            )
            if event_service:
                loop.run_until_complete(event_service.send_message(message))

                # Get conversation info for response
                loop.run_until_complete(
                    self.conversation_service.get_conversation(conversation_id)
                )
        finally:
            loop.close()

        # For now, return a simple response
        # In a full implementation, we would wait for the agent's response
        response_content: list[ContentBlock] = [
            TextContent(text="Message received and processing...")
        ]

        response = PromptResponse(content=response_content)
        return response.model_dump()

    def _handle_session_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle session/cancel notification."""
        notification = SessionCancelNotification.model_validate(params)

        # Check if session exists
        if notification.sessionId in self.sessions:
            # For now, we don't have a way to cancel ongoing operations
            # This would be implemented when we add streaming support
            pass

        # Notifications don't return responses
        return {}

    def run(self) -> None:
        """Run the ACP server."""
        self.transport.run()

    def stop(self) -> None:
        """Stop the ACP server."""
        self.transport.stop()
