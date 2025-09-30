"""OpenHands Agent Client Protocol (ACP) server implementation."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from acp import (
    Agent as ACPAgent,
    AgentSideConnection,
    InitializeRequest,
    InitializeResponse,
    NewSessionRequest,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    SessionNotification,
    stdio_streams,
)
from acp.schema import (
    AgentCapabilities,
    AuthenticateRequest,
    AuthenticateResponse,
    CancelNotification,
    ContentBlock1,
    LoadSessionRequest,
    McpCapabilities,
    PromptCapabilities,
    SessionUpdate2,
    SetSessionModeRequest,
    SetSessionModeResponse,
)
from pydantic import SecretStr

from openhands.agent_server.conversation_service import ConversationService
from openhands.agent_server.models import StartConversationRequest
from openhands.sdk import LLM, Agent, Message, TextContent


logger = logging.getLogger(__name__)


class OpenHandsACPAgent(ACPAgent):
    """OpenHands Agent Client Protocol implementation."""

    def __init__(self, conn: AgentSideConnection, persistence_dir: Path | None = None):
        """Initialize the OpenHands ACP agent.

        Args:
            conn: ACP connection for sending notifications
            persistence_dir: Directory for storing conversation data
        """
        self._conn = conn
        self._persistence_dir = persistence_dir or Path("/tmp/openhands_acp")
        self._persistence_dir.mkdir(parents=True, exist_ok=True)

        # Session management
        self._sessions: dict[str, str] = {}  # session_id -> conversation_id

        # Initialize conversation service (will be started in async method)
        self._conversation_service = ConversationService(
            event_services_path=self._persistence_dir
        )
        self._service_started = False

        logger.info(
            f"OpenHands ACP Agent initialized with persistence_dir: "
            f"{self._persistence_dir}"
        )

    async def _ensure_service_started(self):
        """Ensure the conversation service is started."""
        if not self._service_started:
            await self._conversation_service.__aenter__()
            self._service_started = True

    async def initialize(self, params: InitializeRequest) -> InitializeResponse:
        """Initialize the ACP protocol."""
        logger.info(f"Initializing ACP with protocol version: {params.protocolVersion}")

        return InitializeResponse(
            protocolVersion=params.protocolVersion,
            agentCapabilities=AgentCapabilities(
                loadSession=False,
                mcpCapabilities=McpCapabilities(http=False, sse=False),
                promptCapabilities=PromptCapabilities(
                    audio=False,
                    embeddedContext=False,
                    image=False,
                ),
            ),
        )

    async def authenticate(
        self, params: AuthenticateRequest
    ) -> AuthenticateResponse | None:
        """Authenticate the client (no-op for now)."""
        logger.info("Authentication requested (no-op)")
        return AuthenticateResponse()

    async def newSession(self, params: NewSessionRequest) -> NewSessionResponse:
        """Create a new conversation session."""
        await self._ensure_service_started()
        session_id = str(uuid.uuid4())

        # Create a minimal agent for the conversation
        agent = Agent(
            llm=LLM(
                service_id="acp-agent",
                model="gpt-4o-mini",  # Default model
                api_key=SecretStr("dummy-key"),  # Will be overridden by environment
            )
        )

        # Create a new conversation
        create_request = StartConversationRequest(
            agent=agent,
            working_dir=params.cwd or str(Path.cwd()),
        )

        conversation_info = await self._conversation_service.start_conversation(
            create_request
        )

        # Map session to conversation
        self._sessions[session_id] = str(conversation_info.id)

        logger.info(
            f"Created new session {session_id} -> conversation {conversation_info.id}"
        )

        return NewSessionResponse(sessionId=session_id)

    async def prompt(self, params: PromptRequest) -> PromptResponse:
        """Handle a prompt request."""
        session_id = params.sessionId

        if session_id not in self._sessions:
            raise ValueError(f"Unknown session: {session_id}")

        conversation_id = self._sessions[session_id]

        # Extract text from prompt content blocks
        prompt_text = ""
        for block in params.prompt:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    prompt_text += block.get("text", "")
            else:
                # Handle ContentBlock objects
                if hasattr(block, "type") and block.type == "text":
                    prompt_text += getattr(block, "text", "")

        if not prompt_text.strip():
            return PromptResponse(stopReason="end_turn")

        logger.info(
            f"Processing prompt for session {session_id}: {prompt_text[:100]}..."
        )

        try:
            # Get the event service for this conversation
            event_service = await self._conversation_service.get_event_service(
                UUID(conversation_id)
            )
            if event_service is None:
                raise ValueError(
                    f"No event service for conversation: {conversation_id}"
                )

            # Send the message
            message = Message(role="user", content=[TextContent(text=prompt_text)])
            await event_service.send_message(message)

            # For now, just return success - in a full implementation we would
            # stream the agent's response back via session notifications
            await self._conn.sessionUpdate(
                SessionNotification(
                    sessionId=session_id,
                    update=SessionUpdate2(
                        sessionUpdate="agent_message_chunk",
                        content=ContentBlock1(
                            type="text", text="Message received and processing started."
                        ),
                    ),
                )
            )

            return PromptResponse(stopReason="end_turn")

        except Exception as e:
            logger.error(f"Error processing prompt: {e}")
            # Send error notification
            await self._conn.sessionUpdate(
                SessionNotification(
                    sessionId=session_id,
                    update=SessionUpdate2(
                        sessionUpdate="agent_message_chunk",
                        content=ContentBlock1(type="text", text=f"Error: {str(e)}"),
                    ),
                )
            )
            return PromptResponse(stopReason="error")

    async def cancel(self, params: CancelNotification) -> None:
        """Cancel the current operation (no-op for now)."""
        logger.info("Cancel requested (no-op)")

    async def loadSession(self, params: LoadSessionRequest) -> None:
        """Load a session (not supported)."""
        logger.info("Load session requested (not supported)")

    async def setSessionMode(
        self, params: SetSessionModeRequest
    ) -> SetSessionModeResponse | None:
        """Set session mode (no-op for now)."""
        logger.info("Set session mode requested (no-op)")
        return SetSessionModeResponse()

    async def extMethod(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Extension method (not supported)."""
        logger.info(f"Extension method '{method}' requested (not supported)")
        return {"error": "extMethod not supported"}

    async def extNotification(self, method: str, params: dict[str, Any]) -> None:
        """Extension notification (no-op for now)."""
        logger.info(f"Extension notification '{method}' received (no-op)")


async def run_acp_server(persistence_dir: Path | None = None) -> None:
    """Run the OpenHands ACP server."""
    logger.info("Starting OpenHands ACP server...")

    reader, writer = await stdio_streams()

    def create_agent(conn: AgentSideConnection) -> OpenHandsACPAgent:
        return OpenHandsACPAgent(conn, persistence_dir)

    AgentSideConnection(create_agent, writer, reader)

    # Keep the server running
    await asyncio.Event().wait()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Get persistence directory from command line args
    persistence_dir = None
    if len(sys.argv) > 1:
        persistence_dir = Path(sys.argv[1])

    asyncio.run(run_acp_server(persistence_dir))
