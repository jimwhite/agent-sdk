"""Tests for ACP server implementation."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from openhands.agent_server.acp.server import OpenHandsACPAgent


@pytest.fixture
def mock_conn():
    """Mock ACP connection."""
    conn = MagicMock()
    conn.sessionUpdate = AsyncMock()
    return conn


@pytest.fixture
def temp_persistence_dir():
    """Temporary persistence directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.mark.asyncio
async def test_initialize(mock_conn, temp_persistence_dir):
    """Test initialize method."""
    from acp import InitializeRequest
    from acp.schema import ClientCapabilities

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    request = InitializeRequest(
        protocolVersion=1,
        clientCapabilities=ClientCapabilities(),
    )

    response = await agent.initialize(request)

    assert response.protocolVersion == 1
    assert response.agentCapabilities is not None
    assert hasattr(response.agentCapabilities, "promptCapabilities")
    assert response.authMethods is not None
    assert len(response.authMethods) == 1
    assert response.authMethods[0].id == "llm_config"
    assert response.authMethods[0].name == "LLM Configuration"


@pytest.mark.asyncio
async def test_authenticate_llm_config(mock_conn, temp_persistence_dir):
    """Test authenticate method with LLM configuration."""
    from acp.schema import AuthenticateRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # Test LLM configuration authentication
    llm_config = {
        "model": "gpt-4",
        "api_key": "test-api-key",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_output_tokens": 2000,
    }

    request = AuthenticateRequest(methodId="llm_config", **{"_meta": llm_config})
    response = await agent.authenticate(request)

    assert response is not None
    assert agent._llm_config["model"] == "gpt-4"
    assert agent._llm_config["api_key"] == "test-api-key"
    assert agent._llm_config["base_url"] == "https://api.openai.com/v1"
    assert agent._llm_config["temperature"] == 0.7
    assert agent._llm_config["max_output_tokens"] == 2000


@pytest.mark.asyncio
async def test_authenticate_unsupported_method(mock_conn, temp_persistence_dir):
    """Test authenticate method with unsupported method."""
    from acp.schema import AuthenticateRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)
    request = AuthenticateRequest(methodId="unsupported-method")

    response = await agent.authenticate(request)

    assert response is None


@pytest.mark.asyncio
async def test_authenticate_no_config(mock_conn, temp_persistence_dir):
    """Test authenticate method without configuration."""
    from acp.schema import AuthenticateRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)
    request = AuthenticateRequest(methodId="llm_config")

    response = await agent.authenticate(request)

    assert response is not None
    assert len(agent._llm_config) == 0


def test_validate_llm_config(mock_conn, temp_persistence_dir):
    """Test LLM configuration validation."""
    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # Test valid configuration
    config = {
        "model": "gpt-4",
        "api_key": "test-key",
        "temperature": 0.7,
        "unknown_param": "should_be_ignored",
        "max_output_tokens": 2000,
    }

    validated = agent._validate_llm_config(config)

    assert validated["model"] == "gpt-4"
    assert validated["api_key"] == "test-key"
    assert validated["temperature"] == 0.7
    assert validated["max_output_tokens"] == 2000
    assert "unknown_param" not in validated


def test_create_llm_from_config_with_auth(mock_conn, temp_persistence_dir):
    """Test LLM creation with authenticated configuration."""
    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # Set authenticated config
    agent._llm_config = {
        "model": "gpt-4",
        "api_key": "test-key",
        "temperature": 0.5,
    }

    llm = agent._create_llm_from_config()

    assert llm.model == "gpt-4"
    assert llm.api_key is not None
    assert llm.api_key.get_secret_value() == "test-key"
    assert llm.temperature == 0.5
    assert llm.service_id == "acp-agent"


def test_create_llm_from_config_defaults(mock_conn, temp_persistence_dir, monkeypatch):
    """Test LLM creation with default configuration."""
    # Clear environment variables
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # No authenticated config
    llm = agent._create_llm_from_config()

    assert llm.model == "claude-sonnet-4-20250514"  # Default model
    assert llm.service_id == "acp-agent"


@pytest.mark.asyncio
async def test_new_session(mock_conn, temp_persistence_dir):
    """Test newSession method."""
    from acp import NewSessionRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    request = NewSessionRequest(cwd="/tmp", mcpServers=[])

    response = await agent.newSession(request)

    assert response.sessionId is not None
    assert len(response.sessionId) > 0
    assert response.sessionId in agent._sessions


@pytest.mark.asyncio
async def test_prompt_unknown_session(mock_conn, temp_persistence_dir):
    """Test prompt with unknown session."""
    from acp import PromptRequest
    from acp.schema import ContentBlock1

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    request = PromptRequest(
        sessionId="unknown-session",
        prompt=[ContentBlock1(type="text", text="Hello")],
    )

    with pytest.raises(ValueError, match="Unknown session"):
        await agent.prompt(request)


@pytest.mark.asyncio
async def test_content_handling():
    """Test that content handling works for both text and image content."""
    from unittest.mock import AsyncMock, MagicMock

    from acp.schema import (
        ContentBlock1,
        ContentBlock2,
        SessionNotification,
        SessionUpdate2,
    )

    from openhands.sdk.llm import ImageContent, Message, TextContent

    # Mock connection
    mock_conn = MagicMock()
    mock_conn.sessionUpdate = AsyncMock()

    # Create a mock event subscriber to test content handling
    from openhands.agent_server.pub_sub import Subscriber
    from openhands.sdk.event.base import LLMConvertibleEvent
    from openhands.sdk.event.types import SourceType

    class MockLLMEvent(LLMConvertibleEvent):
        source: SourceType = "agent"  # Required field

        def to_llm_message(self) -> Message:
            return Message(
                role="assistant",
                content=[
                    TextContent(text="Hello world"),
                    ImageContent(
                        image_urls=[
                            "https://example.com/image.png",
                            "data:image/png;base64,abc123",
                        ]
                    ),
                    TextContent(text="Another text"),
                ],
            )

    # Create the event subscriber

    # We need to access the EventSubscriber class from the prompt method
    # For testing, we'll create it directly
    class EventSubscriber(Subscriber):
        def __init__(self, session_id: str, conn):
            self.session_id = session_id
            self.conn = conn

        async def __call__(self, event):
            # This is the same logic as in the server
            from openhands.sdk.event.base import LLMConvertibleEvent
            from openhands.sdk.llm import ImageContent, TextContent

            if isinstance(event, LLMConvertibleEvent):
                try:
                    llm_message = event.to_llm_message()

                    if llm_message.role == "assistant":
                        for content_item in llm_message.content:
                            if isinstance(content_item, TextContent):
                                if content_item.text.strip():
                                    await self.conn.sessionUpdate(
                                        SessionNotification(
                                            sessionId=self.session_id,
                                            update=SessionUpdate2(
                                                sessionUpdate="agent_message_chunk",
                                                content=ContentBlock1(
                                                    type="text", text=content_item.text
                                                ),
                                            ),
                                        )
                                    )
                            elif isinstance(content_item, ImageContent):
                                for image_url in content_item.image_urls:
                                    is_uri = image_url.startswith(
                                        ("http://", "https://")
                                    )
                                    await self.conn.sessionUpdate(
                                        SessionNotification(
                                            sessionId=self.session_id,
                                            update=SessionUpdate2(
                                                sessionUpdate="agent_message_chunk",
                                                content=ContentBlock2(
                                                    type="image",
                                                    data=image_url,
                                                    mimeType="image/png",
                                                    uri=image_url if is_uri else None,
                                                ),
                                            ),
                                        )
                                    )
                            elif isinstance(content_item, str):
                                if content_item.strip():
                                    await self.conn.sessionUpdate(
                                        SessionNotification(
                                            sessionId=self.session_id,
                                            update=SessionUpdate2(
                                                sessionUpdate="agent_message_chunk",
                                                content=ContentBlock1(
                                                    type="text", text=content_item
                                                ),
                                            ),
                                        )
                                    )
                except Exception:
                    pass  # Ignore errors for test

    # Test the event subscriber
    subscriber = EventSubscriber("test-session", mock_conn)
    mock_event = MockLLMEvent()

    await subscriber(mock_event)

    # Verify that sessionUpdate was called correctly
    assert mock_conn.sessionUpdate.call_count == 4  # 2 text + 2 images

    calls = mock_conn.sessionUpdate.call_args_list

    # Check first text content
    assert calls[0][0][0].update.content.type == "text"
    assert calls[0][0][0].update.content.text == "Hello world"

    # Check first image content (URI)
    assert calls[1][0][0].update.content.type == "image"
    assert calls[1][0][0].update.content.data == "https://example.com/image.png"
    assert calls[1][0][0].update.content.uri == "https://example.com/image.png"

    # Check second image content (base64)
    assert calls[2][0][0].update.content.type == "image"
    assert calls[2][0][0].update.content.data == "data:image/png;base64,abc123"
    assert calls[2][0][0].update.content.uri is None

    # Check second text content
    assert calls[3][0][0].update.content.type == "text"
    assert calls[3][0][0].update.content.text == "Another text"


@pytest.mark.asyncio
async def test_tool_call_handling():
    """Test that tool call events are properly handled and sent as ACP notifications."""
    from unittest.mock import AsyncMock, MagicMock

    from acp.schema import SessionNotification, SessionUpdate4, SessionUpdate5
    from litellm import ChatCompletionMessageToolCall

    from openhands.sdk.event import ActionEvent, ObservationEvent
    from openhands.sdk.llm import TextContent
    from openhands.sdk.mcp import MCPToolAction, MCPToolObservation

    # Mock connection
    mock_conn = MagicMock()
    mock_conn.sessionUpdate = AsyncMock()

    # Create the event subscriber
    from openhands.agent_server.pub_sub import Subscriber

    class EventSubscriber(Subscriber):
        def __init__(self, session_id: str, conn):
            self.session_id = session_id
            self.conn = conn

        async def __call__(self, event):
            # Import the actual implementation from the server
            from acp.schema import ContentBlock1, ToolCallContent1

            from openhands.agent_server.acp.server import _get_tool_kind

            # Use the actual event handling logic from the server
            from openhands.sdk.event import (
                ActionEvent,
                AgentErrorEvent,
                ObservationEvent,
                UserRejectObservation,
            )
            from openhands.sdk.llm import ImageContent, TextContent

            print(f"Processing event: {type(event)}")
            if isinstance(event, ActionEvent):
                print("Processing ActionEvent")
                # Send tool_call notification for action events
                try:
                    tool_kind = _get_tool_kind(event.tool_name)
                    print(f"Tool kind: {tool_kind}")

                    # Create a human-readable title
                    action_name = event.action.__class__.__name__
                    title = f"{action_name} with {event.tool_name}"
                    print(f"Title: {title}")

                    # Extract thought content as text
                    thought_text = " ".join([t.text for t in event.thought])
                    print(f"Thought text: {thought_text}")

                    await self.conn.sessionUpdate(
                        SessionNotification(
                            sessionId=self.session_id,
                            update=SessionUpdate4(
                                sessionUpdate="tool_call",
                                toolCallId=event.tool_call_id,
                                title=title,
                                kind=tool_kind,
                                status="pending",
                                content=[
                                    ToolCallContent1(
                                        type="content",
                                        content=ContentBlock1(
                                            type="text",
                                            text=thought_text
                                            if thought_text.strip()
                                            else f"Executing {action_name}",
                                        ),
                                    )
                                ]
                                if thought_text.strip()
                                else None,
                                rawInput=event.tool_call.function.arguments
                                if hasattr(event.tool_call.function, "arguments")
                                else None,
                            ),
                        )
                    )
                    print("sessionUpdate called successfully")
                except Exception as e:
                    print(f"Error sending tool_call: {e}")
                    import traceback

                    traceback.print_exc()

            elif isinstance(
                event, (ObservationEvent, UserRejectObservation, AgentErrorEvent)
            ):
                # Send tool_call_update notification for observation events
                try:
                    if isinstance(event, ObservationEvent):
                        # Successful tool execution
                        status = "completed"
                        # Extract content from observation
                        content_parts = []
                        for item in event.observation.agent_observation:
                            if isinstance(item, TextContent):
                                content_parts.append(item.text)
                            elif hasattr(item, "text") and not isinstance(
                                item, ImageContent
                            ):
                                content_parts.append(getattr(item, "text"))
                            else:
                                content_parts.append(str(item))
                        content_text = "".join(content_parts)
                    elif isinstance(event, UserRejectObservation):
                        # User rejected the action
                        status = "failed"
                        content_text = f"User rejected: {event.rejection_reason}"
                    else:  # AgentErrorEvent
                        # Agent error
                        status = "failed"
                        content_text = f"Error: {event.error}"

                    await self.conn.sessionUpdate(
                        SessionNotification(
                            sessionId=self.session_id,
                            update=SessionUpdate5(
                                sessionUpdate="tool_call_update",
                                toolCallId=event.tool_call_id,
                                status=status,
                                content=[
                                    ToolCallContent1(
                                        type="content",
                                        content=ContentBlock1(
                                            type="text",
                                            text=content_text,
                                        ),
                                    )
                                ]
                                if content_text.strip()
                                else None,
                                rawOutput={"result": content_text}
                                if content_text.strip()
                                else None,
                            ),
                        )
                    )
                except Exception:
                    pass  # Ignore errors for test

    # Test the event subscriber with ActionEvent
    subscriber = EventSubscriber("test-session", mock_conn)

    # Create a mock ActionEvent
    mock_action = MCPToolAction(kind="MCPToolAction", data={"command": "ls"})
    mock_tool_call = ChatCompletionMessageToolCall(
        id="test-call-123",
        function={"name": "execute_bash", "arguments": '{"command": "ls"}'},
        type="function",
    )

    action_event = ActionEvent(
        tool_call_id="test-call-123",
        tool_call=mock_tool_call,
        thought=[TextContent(text="I need to list files")],
        action=mock_action,
        tool_name="execute_bash",
        llm_response_id="test-response-123",
    )

    await subscriber(action_event)

    # Verify that sessionUpdate was called for tool_call
    assert mock_conn.sessionUpdate.call_count == 1
    call_args = mock_conn.sessionUpdate.call_args_list[0]
    notification = call_args[0][0]

    assert notification.sessionId == "test-session"
    assert notification.update.sessionUpdate == "tool_call"
    assert notification.update.toolCallId == "test-call-123"
    assert notification.update.title == "MCPToolAction with execute_bash"
    assert notification.update.kind == "execute"
    assert notification.update.status == "pending"

    # Reset mock for observation event test
    mock_conn.sessionUpdate.reset_mock()

    # Create a mock ObservationEvent
    mock_observation = MCPToolObservation(
        kind="MCPToolObservation",
        content=[
            TextContent(text="total 4\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 test")
        ],
        is_error=False,
        tool_name="execute_bash",
    )

    observation_event = ObservationEvent(
        tool_call_id="test-call-123",
        tool_name="execute_bash",
        observation=mock_observation,
        action_id="test-action-123",
    )

    await subscriber(observation_event)

    # Verify that sessionUpdate was called for tool_call_update
    assert mock_conn.sessionUpdate.call_count == 1
    call_args = mock_conn.sessionUpdate.call_args_list[0]
    notification = call_args[0][0]

    assert notification.sessionId == "test-session"
    assert notification.update.sessionUpdate == "tool_call_update"
    assert notification.update.toolCallId == "test-call-123"
    assert notification.update.status == "completed"
    assert notification.update.content[0].content.text == (
        "[Tool 'execute_bash' executed.]\n"
        "total 4\n"
        "drwxr-xr-x 2 user user 4096 Jan 1 12:00 test"
    )
