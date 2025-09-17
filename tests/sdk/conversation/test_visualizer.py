"""Tests for the conversation visualizer and event visualization."""

import json
from collections.abc import Sequence

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function
from rich.text import Text

from openhands.sdk.conversation.visualizer import (
    DARK_THEME,
    HIGH_CONTRAST_THEME,
    LIGHT_THEME,
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
from openhands.sdk.tool import ActionBase


class MockAction(ActionBase):
    """Mock action for testing."""

    command: str = "test command"
    working_dir: str = "/tmp"


class CustomAction(ActionBase):
    """Custom action with overridden visualize method."""

    task_list: list[dict] = []

    @property
    def visualize(self) -> Text:
        """Custom visualization for task tracker."""
        content = Text()
        content.append("Task Tracker Action\n", style="bold")
        content.append(f"Tasks: {len(self.task_list)}")
        for i, task in enumerate(self.task_list):
            content.append(f"\n  {i + 1}. {task.get('title', 'Untitled')}")
        return content


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
    """Test that ActionBase has a visualize property."""
    action = MockAction(command="echo hello", working_dir="/home")

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
    """Test that custom actions can override visualize method."""
    tasks = [
        {"title": "Task 1", "status": "todo"},
        {"title": "Task 2", "status": "done"},
    ]
    action = CustomAction(task_list=tasks)

    result = action.visualize
    assert isinstance(result, Text)

    text_content = result.plain
    assert "Task Tracker Action" in text_content
    assert "Tasks: 2" in text_content
    assert "1. Task 1" in text_content
    assert "2. Task 2" in text_content


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
    from openhands.sdk.tool import ObservationBase

    class MockObservation(ObservationBase):
        content: str = "Command output"

        @property
        def agent_observation(self) -> Sequence[TextContent | ImageContent]:
            return [TextContent(text=self.content)]

    observation = MockObservation(
        content="total 4\ndrwxr-xr-x 2 user user 4096 Jan 1 12:00 ."
    )
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


def test_color_theme_customization():
    """Test that custom color themes work correctly."""
    custom_theme = {
        "observation": "orange",
        "pause": "cyan",
        "error": "bright_red",
    }

    visualizer = ConversationVisualizer(color_theme=custom_theme)

    # Check that custom colors are applied
    assert visualizer._colors["observation"] == "orange"
    assert visualizer._colors["pause"] == "cyan"
    assert visualizer._colors["error"] == "bright_red"

    # Check that non-overridden colors remain default
    assert visualizer._colors["action"] == "blue"  # default value
    assert visualizer._colors["system"] == "magenta"  # default value


def test_predefined_themes():
    """Test that predefined themes are available and work."""
    # Test LIGHT_THEME
    light_visualizer = ConversationVisualizer(color_theme=LIGHT_THEME)
    assert light_visualizer._colors["observation"] == "blue"
    assert light_visualizer._colors["message_user"] == "dark_orange"

    # Test DARK_THEME
    dark_visualizer = ConversationVisualizer(color_theme=DARK_THEME)
    assert dark_visualizer._colors["observation"] == "yellow"
    assert dark_visualizer._colors["pause"] == "bright_yellow"

    # Test HIGH_CONTRAST_THEME
    hc_visualizer = ConversationVisualizer(color_theme=HIGH_CONTRAST_THEME)
    assert hc_visualizer._colors["observation"] == "bright_white"
    assert hc_visualizer._colors["error"] == "bright_red"


def test_create_default_visualizer_with_theme():
    """Test that create_default_visualizer accepts color_theme parameter."""
    custom_theme = {"observation": "green", "action": "red"}

    visualizer = create_default_visualizer(color_theme=custom_theme)

    assert isinstance(visualizer, ConversationVisualizer)
    assert visualizer._colors["observation"] == "green"
    assert visualizer._colors["action"] == "red"


def test_color_theme_in_panel_creation():
    """Test that custom colors are used in panel creation."""
    custom_theme = {"observation": "green"}
    visualizer = ConversationVisualizer(color_theme=custom_theme)

    # Create a mock observation event
    from openhands.sdk.tool import ObservationBase

    class MockObservation(ObservationBase):
        content: str = "Test output"

        @property
        def agent_observation(self):
            from openhands.sdk.llm import TextContent

            return [TextContent(text=self.content)]

    observation = MockObservation(content="Test output")
    event = ObservationEvent(
        observation=observation,
        action_id="action_123",
        tool_name="test",
        tool_call_id="call_123",
    )

    panel = visualizer._create_event_panel(event)
    assert panel is not None
    # The panel should use the custom green color for observation
    assert panel.border_style == "green"


def test_metrics_reasoning_color_customization():
    """Test that reasoning tokens color can be customized."""
    custom_theme = {"metrics_reasoning": "orange"}
    visualizer = ConversationVisualizer(color_theme=custom_theme)

    # Create an event with reasoning tokens
    action = MockAction(command="test")
    metrics = MetricsSnapshot(
        accumulated_token_usage=TokenUsage(
            prompt_tokens=1000,
            completion_tokens=500,
            reasoning_tokens=200,
        ),
        accumulated_cost=0.01,
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
    # Should contain the custom orange color for reasoning tokens
    assert "[orange]" in subtitle and "[/orange]" in subtitle


def test_automatic_theme_detection():
    """Test automatic theme detection functionality."""
    import os
    from unittest.mock import patch

    # Test light theme detection
    with patch.dict(
        os.environ, {"TERM_PROGRAM": "Apple_Terminal", "COLORFGBG": "0;15"}
    ):
        from openhands.sdk.conversation.visualizer import (
            _detect_terminal_theme,
            _get_auto_theme_colors,
        )

        assert _detect_terminal_theme() == "light"
        colors = _get_auto_theme_colors()
        assert colors["observation"] == "blue"  # Should use LIGHT_THEME

    # Test dark theme detection
    with patch.dict(
        os.environ, {"TERM_PROGRAM": "Apple_Terminal", "COLORFGBG": "15;0"}
    ):
        assert _detect_terminal_theme() == "dark"
        colors = _get_auto_theme_colors()
        assert colors["observation"] == "yellow"  # Should use DARK_THEME

    # Test unknown theme (should use default)
    with patch.dict(os.environ, {}, clear=True):
        assert _detect_terminal_theme() is None
        colors = _get_auto_theme_colors()
        assert colors["observation"] == "bright_cyan"  # Should use _DEFAULT_COLORS


def test_visualizer_with_automatic_theme():
    """Test that visualizer uses automatic theme detection when no theme specified."""
    import os
    from unittest.mock import patch

    # Test with light theme environment
    with patch.dict(
        os.environ, {"TERM_PROGRAM": "Apple_Terminal", "COLORFGBG": "0;15"}
    ):
        visualizer = ConversationVisualizer()  # No color_theme specified
        assert (
            visualizer._colors["observation"] == "blue"
        )  # Should auto-detect light theme

    # Test with explicit theme override
    with patch.dict(
        os.environ, {"TERM_PROGRAM": "Apple_Terminal", "COLORFGBG": "0;15"}
    ):
        custom_theme = {"observation": "orange"}
        visualizer = ConversationVisualizer(color_theme=custom_theme)
        assert (
            visualizer._colors["observation"] == "orange"
        )  # Should use explicit theme
