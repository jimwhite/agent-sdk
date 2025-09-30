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
    AuthMethod,
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
from openhands.sdk import LLM, Message, TextContent
from openhands.tools.preset.default import get_default_agent


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
        self._llm_config: dict[str, Any] = {}  # Store LLM configuration from auth

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
            authMethods=[
                AuthMethod(
                    id="llm_config",
                    name="LLM Configuration",
                    description=(
                        "Configure LLM settings including model, API key, "
                        "and other parameters"
                    ),
                )
            ],
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
        """Authenticate the client and configure LLM settings."""
        logger.info(f"Authentication requested with method: {params.methodId}")

        if params.methodId == "llm_config":
            # Extract LLM configuration from the _meta field
            if params.field_meta:
                llm_config = params.field_meta
                logger.info("Received LLM configuration via authentication")

                # Validate and store LLM configuration
                self._llm_config = self._validate_llm_config(llm_config)
                logger.info(
                    f"LLM configuration stored: {list(self._llm_config.keys())}"
                )
            else:
                logger.warning("No LLM configuration provided in authentication")

            return AuthenticateResponse()
        else:
            logger.error(f"Unsupported authentication method: {params.methodId}")
            return None

    def _validate_llm_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate and sanitize LLM configuration."""
        # Define allowed LLM configuration parameters based on the LLM class
        allowed_params = {
            "model",
            "api_key",
            "base_url",
            "api_version",
            "aws_access_key_id",
            "aws_secret_access_key",
            "aws_region_name",
            "openrouter_site_url",
            "openrouter_app_name",
            "num_retries",
            "retry_multiplier",
            "retry_min_wait",
            "retry_max_wait",
            "timeout",
            "max_message_chars",
            "temperature",
            "top_p",
            "top_k",
            "custom_llm_provider",
            "max_input_tokens",
            "max_output_tokens",
            "input_cost_per_token",
            "output_cost_per_token",
            "ollama_base_url",
            "drop_params",
            "modify_params",
            "disable_vision",
            "disable_stop_word",
            "caching_prompt",
            "log_completions",
            "log_completions_folder",
            "custom_tokenizer",
            "native_tool_calling",
            "reasoning_effort",
            "seed",
            "safety_settings",
        }

        # Filter and validate configuration
        validated_config = {}
        for key, value in config.items():
            if key in allowed_params and value is not None:
                validated_config[key] = value
            elif key not in allowed_params:
                logger.warning(f"Unknown LLM parameter ignored: {key}")

        return validated_config

    def _create_llm_from_config(self) -> LLM:
        """Create an LLM instance using stored configuration or defaults."""
        import os

        # Start with default configuration
        llm_kwargs: dict[str, Any] = {
            "service_id": "acp-agent",
            "model": "claude-sonnet-4-20250514",  # Default model
        }

        # Apply user-provided configuration from authentication
        if self._llm_config:
            # Type-safe update of configuration
            for key, value in self._llm_config.items():
                llm_kwargs[key] = value
            logger.info(
                f"Using authenticated LLM config: {list(self._llm_config.keys())}"
            )
        else:
            # Fallback to environment variables if no auth config provided
            logger.info("No authenticated LLM config, using environment/defaults")

            # Try to get API key from environment
            api_key = os.getenv("LITELLM_API_KEY") or os.getenv("OPENAI_API_KEY")
            if api_key:
                llm_kwargs["api_key"] = api_key

                # Configure for litellm proxy if available
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
                logger.warning("No API key found. Agent responses may not work.")
                llm_kwargs["api_key"] = "dummy-key"

        # Convert api_key to SecretStr if it's a string
        if "api_key" in llm_kwargs and isinstance(llm_kwargs["api_key"], str):
            llm_kwargs["api_key"] = SecretStr(llm_kwargs["api_key"])

        # Convert other secret fields to SecretStr if needed
        secret_fields = ["aws_access_key_id", "aws_secret_access_key"]
        for field in secret_fields:
            if field in llm_kwargs and isinstance(llm_kwargs[field], str):
                llm_kwargs[field] = SecretStr(llm_kwargs[field])

        logger.info(f"Creating LLM with model: {llm_kwargs.get('model', 'unknown')}")
        return LLM(**llm_kwargs)

    async def newSession(self, params: NewSessionRequest) -> NewSessionResponse:
        """Create a new conversation session."""
        await self._ensure_service_started()
        session_id = str(uuid.uuid4())

        # Create a properly configured agent for the conversation
        llm = self._create_llm_from_config()

        agent = get_default_agent(llm=llm, cli_mode=True)

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

            # Subscribe to events and send them directly via sessionUpdate
            from openhands.agent_server.pub_sub import Subscriber
            from openhands.sdk.event.base import LLMConvertibleEvent

            class EventSubscriber(Subscriber):
                def __init__(self, session_id: str, conn):
                    self.session_id = session_id
                    self.conn = conn

                async def __call__(self, event):
                    # Send all LLMConvertibleEvent events as session updates
                    if isinstance(event, LLMConvertibleEvent):
                        try:
                            llm_message = event.to_llm_message()

                            # Send the event as a session update
                            if llm_message.role == "assistant":
                                # Extract text content from the message
                                text_content = ""
                                for content_item in llm_message.content:
                                    if isinstance(content_item, TextContent):
                                        text_content += content_item.text
                                    elif isinstance(content_item, str):
                                        text_content += content_item

                                if text_content.strip():
                                    # Send streaming update
                                    await self.conn.sessionUpdate(
                                        SessionNotification(
                                            sessionId=self.session_id,
                                            update=SessionUpdate2(
                                                sessionUpdate="agent_message_chunk",
                                                content=ContentBlock1(
                                                    type="text", text=text_content
                                                ),
                                            ),
                                        )
                                    )
                        except Exception as e:
                            logger.debug(f"Error processing LLMConvertibleEvent: {e}")

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
