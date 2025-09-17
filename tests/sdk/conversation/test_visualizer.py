"""Tests for the conversation visualizer and event visualization."""

import json
from collections.abc import Sequence

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function
from rich.text import Text

from openhands.sdk.conversation.visualizer import (
    ConversationVisualizer,
    create_default_visualizer,
)
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    MessageEvent,
    ObservationEvent,
    PauseEvent,
    SystemPromptEvent,
)
from openhands.sdk.llm import ImageContent, Message, TextContent
from openhands.sdk.llm.utils.metrics import MetricsSnapshot, TokenUsage
from openhands.sdk.tool.schema import Schema, SchemaField, SchemaInstance
from openhands.sdk.tool.schema.types import SchemaFieldType


def create_mock_action() -> SchemaInstance:
    """Create a mock action for testing."""
    schema = Schema(
        name="MockAction",
        fields=[
            SchemaField(name="command", type=SchemaFieldType.from_type(str), description="Command"),
            SchemaField(name="working_dir", type=SchemaFieldType.from_type(str), description="Working directory")
        ]
    )
    return SchemaInstance(
        name="MockAction",
        definition=schema,
        data={"command": "test command", "working_dir": "/tmp"}
    )


def create_custom_action() -> SchemaInstance:
    """Create a custom action with task list for testing."""
    schema = Schema(
        name="CustomAction",
        fields=[
            SchemaField(name="task_list", type=SchemaFieldType.from_type(list), description="Task list")
        ]
    )
    return SchemaInstance(
        name="CustomAction",
        definition=schema,
        data={"task_list": []}
    )


def create_tool_call(
    call_id: str, function_name: str, arguments: dict
) -> ChatCompletionMessageToolCall:
    """Helper to create a ChatCompletionMessageToolCall."""
    return ChatCompletionMessageToolCall(
        id=call_id,
        function=Function(name=function_name, arguments=json.dumps(arguments)),
        type="function",
    )


def test_action_base_visualize():
    """Test that SchemaInstance has a visualize property."""
    action = create_mock_action()
    action.data["command"] = "echo hello"
    action.data["working_dir"] = "/home"

    result = action.visualize
    assert isinstance(result, Text)

    # Check that it contains action name and fields
    text_content = result.plain
    assert "MockAction" in text_content
    assert "command" in text_content
    assert "echo hello" in text_content
    assert "working_dir" in text_content
    assert "/home" in text_content


def test_custom_action_visualize():
    """Test that custom actions can have custom visualization."""
    tasks = [
        {"title": "Task 1", "status": "todo"},
        {"title": "Task 2", "status": "done"},
    ]
    action = create_custom_action()
    action.data["task_list"] = tasks

    # For now, just test the default visualization since we don't have custom visualize method
    result = action.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "CustomAction" in text_content
    assert "task_list" in text_content


def test_system_prompt_event_visualize():
    """Test SystemPromptEvent visualization."""
    event = SystemPromptEvent(
        system_prompt=TextContent(text="You are a helpful assistant."),
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "description": "A test tool for demonstration",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )

    result = event.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "System Prompt:" in text_content
    assert "You are a helpful assistant." in text_content
    assert "Tools Available: 1" in text_content
    assert "test_tool" in text_content


def test_action_event_visualize():
    """Test ActionEvent visualization."""
    action = MockAction(command="ls -la", working_dir="/tmp")
    tool_call = create_tool_call("call_123", "bash", {"command": "ls -la"})
    event = ActionEvent(
        thought=[TextContent(text="I need to list files")],
        reasoning_content="Let me check the directory contents",
        action=action,
        tool_name="bash",
        tool_call_id="call_123",
        tool_call=tool_call,
        llm_response_id="response_456",
    )

    result = event.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "Reasoning:" in text_content
    assert "Let me check the directory contents" in text_content
    assert "Thought:" in text_content
    assert "I need to list files" in text_content
    assert "MockAction" in text_content
    assert "ls -la" in text_content


def test_observation_event_visualize():
    """Test ObservationEvent visualization."""
    def create_mock_observation() -> SchemaInstance:
        """Create a mock observation for testing."""
        schema = Schema(
            name="MockObservation",
            fields=[
                SchemaField(name="content", type=SchemaFieldType.from_type(str), description="Content")
            ]
        )
        return SchemaInstance(
            name="MockObservation",
            definition=schema,
            data={"content": "Command output"}
        )

    observation = create_mock_observation()
    observation.data["content"] = "total 4\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 ."
    event = ObservationEvent(
        observation=observation,
        action_id="action_123",
        tool_name="bash",
        tool_call_id="call_123",
    )

    result = event.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "Tool: bash" in text_content
    assert "Result:" in text_content
    assert "total 4" in text_content


def test_message_event_visualize():
    """Test MessageEvent visualization."""
    message = Message(
        role="user",
        content=[TextContent(text="Hello, how can you help me?")],
    )
    event = MessageEvent(
        source="user",
        llm_message=message,
        activated_microagents=["helper", "analyzer"],
        extended_content=[TextContent(text="Additional context")],
    )

    result = event.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "Hello, how can you help me?" in text_content
    assert "Activated Microagents: helper, analyzer" in text_content
    assert "Prompt Extension based on Agent Context:" in text_content
    assert "Additional context" in text_content


def test_agent_error_event_visualize():
    """Test AgentErrorEvent visualization."""
    event = AgentErrorEvent(
        error="Failed to execute command: permission denied",
    )

    result = event.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "Error Details:" in text_content
    assert "Failed to execute command: permission denied" in text_content


def test_pause_event_visualize():
    """Test PauseEvent visualization."""
    event = PauseEvent()

    result = event.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "Conversation Paused" in text_content


def test_conversation_visualizer_initialization():
    """Test ConversationVisualizer can be initialized."""
    visualizer = ConversationVisualizer()
    assert visualizer is not None
    assert hasattr(visualizer, "on_event")
    assert hasattr(visualizer, "_create_event_panel")


def test_create_default_visualizer():
    """Test create_default_visualizer function."""
    visualizer = create_default_visualizer()
    assert isinstance(visualizer, ConversationVisualizer)


def test_visualizer_event_panel_creation():
    """Test that visualizer creates panels for different event types."""
    visualizer = ConversationVisualizer()

    # Test with a simple action event
    action = MockAction(command="test")
    tool_call = create_tool_call("call_1", "test", {})
    event = ActionEvent(
        thought=[TextContent(text="Testing")],
        action=action,
        tool_name="test",
        tool_call_id="call_1",
        tool_call=tool_call,
        llm_response_id="response_1",
    )

    panel = visualizer._create_event_panel(event)
    assert panel is not None
    assert hasattr(panel, "renderable")


def test_metrics_formatting():
    """Test metrics subtitle formatting."""
    visualizer = ConversationVisualizer()

    # Create an event with metrics
    action = MockAction(command="test")
    metrics = MetricsSnapshot(
        accumulated_token_usage=TokenUsage(
            prompt_tokens=1500,
            completion_tokens=500,
            cache_read_tokens=300,
            reasoning_tokens=200,
        ),
        accumulated_cost=0.0234,
    )

    tool_call = create_tool_call("call_1", "test", {})
    event = ActionEvent(
        thought=[TextContent(text="Testing")],
        action=action,
        tool_name="test",
        tool_call_id="call_1",
        tool_call=tool_call,
        llm_response_id="response_1",
        metrics=metrics,
    )

    subtitle = visualizer._format_metrics_subtitle(event)
    assert subtitle is not None
    assert "1.50K" in subtitle  # Input tokens abbreviated
    assert "500" in subtitle  # Output tokens
    assert "20.00%" in subtitle  # Cache hit rate
    assert "200" in subtitle  # Reasoning tokens
    assert "0.0234" in subtitle  # Cost


def test_event_base_fallback_visualize():
    """Test that EventBase provides fallback visualization."""
    from openhands.sdk.event.base import EventBase
    from openhands.sdk.event.types import SourceType

    class UnknownEvent(EventBase):
        source: SourceType = "agent"

    event = UnknownEvent()
    result = event.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "Unknown event type: UnknownEvent" in text_content
