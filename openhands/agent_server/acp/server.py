"""OpenHands Agent Client Protocol (ACP) server implementation."""

import asyncio
import logging
import os
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
    AuthMethod,
    CancelNotification,
    ContentBlock1,
    LoadSessionRequest,
    McpCapabilities,
    McpServer1,
    McpServer2,
    McpServer3,
    PromptCapabilities,
    SessionUpdate2,
    SetSessionModeRequest,
    SetSessionModeResponse,
)

from openhands.agent_server.conversation_service import ConversationService
from openhands.agent_server.models import StartConversationRequest
from openhands.sdk import Message, TextContent
from openhands.sdk.llm import LLM
from openhands.tools.preset.default import get_default_agent

from .events import EventSubscriber


logger = logging.getLogger(__name__)


def convert_acp_mcp_servers_to_openhands_config(
    acp_mcp_servers: list[McpServer1 | McpServer2 | McpServer3],
) -> dict[str, Any]:
    """Convert ACP MCP server configurations to OpenHands agent mcp_config format.

    Args:
        acp_mcp_servers: List of ACP MCP server configurations

    Returns:
        Dictionary in OpenHands mcp_config format
    """
    mcp_servers = {}

    for server in acp_mcp_servers:
        if isinstance(server, McpServer3):
            # Command-line executable MCP server (supported by OpenHands)
            mcp_servers[server.name] = {
                "command": server.command,
                "args": server.args,
            }
            # Add environment variables if provided
            if server.env:
                env_dict = {env_var.name: env_var.value for env_var in server.env}
                mcp_servers[server.name]["env"] = env_dict
        elif isinstance(server, (McpServer1, McpServer2)):
            # HTTP/SSE MCP servers - not directly supported by OpenHands yet
            # Log a warning for now
            server_type = "HTTP" if isinstance(server, McpServer1) else "SSE"
            logger.warning(
                f"MCP server '{server.name}' uses {server_type} transport "
                f"which is not yet supported by OpenHands. Skipping."
            )
            continue

    return {"mcpServers": mcp_servers} if mcp_servers else {}


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
        self._llm_params: dict[str, Any] = {}  # Store LLM parameters from auth

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

        # Check if we have API keys available from environment
        has_api_key = bool(
            os.getenv("OPENAI_API_KEY")
            or os.getenv("ANTHROPIC_API_KEY")
            or os.getenv("LITELLM_API_KEY")
        )

        # Only require authentication if no API key is available
        auth_methods = []
        if not has_api_key:
            auth_methods = [
                AuthMethod(
                    id="llm_config",
                    name="LLM Configuration",
                    description=(
                        "Configure LLM settings including model, API key, "
                        "and other parameters"
                    ),
                )
            ]
            logger.info("No API key found in environment, requiring authentication")
        else:
            logger.info("API key found in environment, authentication not required")

        return InitializeResponse(
            protocolVersion=params.protocolVersion,
            authMethods=auth_methods,
            agentCapabilities=AgentCapabilities(
                loadSession=False,
                mcpCapabilities=McpCapabilities(http=True, sse=True),
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
        """Authenticate the client and configure LLM settings."""
        logger.info(f"Authentication requested with method: {params.methodId}")

        if params.methodId == "llm_config":
            # Extract LLM configuration from the _meta field
            if params.field_meta:
                self._llm_params = params.field_meta
                logger.info("Received LLM configuration via authentication")
                logger.info(f"LLM parameters stored: {list(self._llm_params.keys())}")
            else:
                logger.warning("No LLM configuration provided in authentication")

            return AuthenticateResponse()
        else:
            logger.error(f"Unsupported authentication method: {params.methodId}")
            return None

    async def newSession(self, params: NewSessionRequest) -> NewSessionResponse:
        """Create a new conversation session."""
        await self._ensure_service_started()
        session_id = str(uuid.uuid4())

        try:
            # Create a properly configured agent for the conversation
            logger.info(f"Creating LLM with params: {list(self._llm_params.keys())}")

            # Create LLM with provided parameters or defaults
            llm_kwargs = {}
            if self._llm_params:
                # Use authenticated parameters
                llm_kwargs.update(self._llm_params)
            else:
                # Use environment defaults
                api_key = os.getenv("LITELLM_API_KEY") or os.getenv("OPENAI_API_KEY")
                if api_key:
                    llm_kwargs["api_key"] = api_key
                    if os.getenv("LITELLM_API_KEY"):
                        llm_kwargs.update(
                            {
                                "model": (
                                    "litellm_proxy/anthropic/claude-sonnet-4-5-20250929"
                                ),
                                "base_url": "https://llm-proxy.eval.all-hands.dev",
                                "drop_params": True,
                            }
                        )
                    else:
                        llm_kwargs["model"] = "gpt-4o-mini"
                else:
                    logger.warning("No API key found. Using dummy key.")
                    llm_kwargs["api_key"] = "dummy-key"

            # Add required service_id
            llm_kwargs["service_id"] = "acp-agent"

            llm = LLM(**llm_kwargs)
            logger.info(f"Created LLM with model: {llm.model}")

            logger.info("Creating agent with MCP configuration")

            # Process MCP servers from the request
            mcp_config = {}
            if params.mcpServers:
                logger.info(
                    f"Processing {len(params.mcpServers)} MCP servers from request"
                )
                client_mcp_config = convert_acp_mcp_servers_to_openhands_config(
                    params.mcpServers
                )
                if client_mcp_config:
                    mcp_config.update(client_mcp_config)
                    server_names = list(client_mcp_config.get("mcpServers", {}).keys())
                    logger.info(f"Added client MCP servers: {server_names}")

            # Get default agent with custom MCP config if provided
            if mcp_config:
                # Import Agent and create custom agent with MCP config
                from openhands.sdk import Agent
                from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
                from openhands.tools.preset.default import (
                    get_default_condenser,
                    get_default_tools,
                )

                tool_specs = get_default_tools(enable_browser=False)  # CLI mode
                agent = Agent(
                    llm=llm,
                    tools=tool_specs,
                    mcp_config=mcp_config,
                    filter_tools_regex="^(?!repomix)(.*)|^repomix.*pack_codebase.*$",
                    system_prompt_kwargs={"cli_mode": True},
                    condenser=get_default_condenser(
                        llm=llm.model_copy(update={"service_id": "condenser"})
                    ),
                    security_analyzer=LLMSecurityAnalyzer(),
                )
                server_names = list(mcp_config.get("mcpServers", {}).keys())
                logger.info(f"Created custom agent with MCP servers: {server_names}")
            else:
                # Use default agent
                agent = get_default_agent(llm=llm, cli_mode=True)
                logger.info("Created default agent with built-in MCP servers")

            # Create a new conversation
            from openhands.sdk.workspace.local import LocalWorkspace

            # Validate working directory
            working_dir = params.cwd or str(Path.cwd())
            working_path = Path(working_dir)

            logger.info(f"Using working directory: {working_dir}")

            # Create directory if it doesn't exist
            if not working_path.exists():
                logger.warning(
                    f"Working directory {working_dir} doesn't exist, creating it"
                )
                working_path.mkdir(parents=True, exist_ok=True)

            if not working_path.is_dir():
                raise ValueError(
                    f"Working directory path is not a directory: {working_dir}"
                )

            workspace = LocalWorkspace(working_dir=str(working_path))

            create_request = StartConversationRequest(
                agent=agent,
                workspace=workspace,
            )

            logger.info("Starting conversation")
            conversation_info = await self._conversation_service.start_conversation(
                create_request
            )

            # Map session to conversation
            self._sessions[session_id] = str(conversation_info.id)

            logger.info(
                f"Created new session {session_id} -> "
                f"conversation {conversation_info.id}"
            )

            return NewSessionResponse(sessionId=session_id)

        except Exception as e:
            logger.error(f"Failed to create new session: {e}", exc_info=True)
            raise

    async def prompt(self, params: PromptRequest) -> PromptResponse:
        """Handle a prompt request."""
        session_id = params.sessionId

        if session_id not in self._sessions:
            raise ValueError(f"Unknown session: {session_id}")

        conversation_id = self._sessions[session_id]

        # Extract text from prompt - handle both string and array formats
        prompt_text = ""
        if isinstance(params.prompt, str):
            prompt_text = params.prompt
        elif isinstance(params.prompt, list):
            for block in params.prompt:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        prompt_text += block.get("text", "")
                else:
                    # Handle ContentBlock objects
                    if hasattr(block, "type") and block.type == "text":
                        prompt_text += getattr(block, "text", "")
        else:
            # Handle single ContentBlock object
            if hasattr(params.prompt, "type") and params.prompt.type == "text":
                prompt_text = getattr(params.prompt, "text", "")

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

            # Send the message and listen for events
            message = Message(role="user", content=[TextContent(text=prompt_text)])
            await event_service.send_message(message)

            # Subscribe to events using the extracted EventSubscriber
            subscriber = EventSubscriber(session_id, self._conn)
            subscriber_id = await event_service.subscribe_to_events(subscriber)

            try:
                # Start the agent processing and wait for completion
                await event_service.run()
            finally:
                # Unsubscribe from events
                await event_service.unsubscribe_from_events(subscriber_id)

            # Return the final response
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
