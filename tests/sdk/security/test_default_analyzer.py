"""Tests for DefaultSecurityAnalyzer."""

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function

from openhands.sdk.event import ActionEvent, MessageEvent
from openhands.sdk.llm import Message, TextContent
from openhands.sdk.security.default_analyzer import DefaultSecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.tool.builtins import FinishAction


def test_default_analyzer_always_returns_unknown():
    """Test that DefaultSecurityAnalyzer always returns UNKNOWN risk."""
    analyzer = DefaultSecurityAnalyzer()

    # Create a mock action event
    tool_call = ChatCompletionMessageToolCall(
        id="test_call_id",
        type="function",
        function=Function(name="finish", arguments='{"message": "test"}'),
    )

    action_event = ActionEvent(
        source="agent",
        thought=[TextContent(text="Test thought")],
        action=FinishAction(message="test"),
        tool_name="finish",
        tool_call_id="test_call_id",
        tool_call=tool_call,
        llm_response_id="response_1",
    )

    # Test that it always returns UNKNOWN
    risk = analyzer.security_risk(action_event)
    assert risk == SecurityRisk.UNKNOWN


def test_default_analyzer_analyze_pending_actions():
    """Test that DefaultSecurityAnalyzer correctly analyzes multiple actions."""
    analyzer = DefaultSecurityAnalyzer()

    # Create multiple mock action events
    tool_call_1 = ChatCompletionMessageToolCall(
        id="test_call_id_1",
        type="function",
        function=Function(name="finish", arguments='{"message": "test1"}'),
    )
    tool_call_2 = ChatCompletionMessageToolCall(
        id="test_call_id_2",
        type="function",
        function=Function(name="finish", arguments='{"message": "test2"}'),
    )

    action_events = [
        ActionEvent(
            source="agent",
            thought=[TextContent(text="Test thought 1")],
            action=FinishAction(message="test1"),
            tool_name="finish",
            tool_call_id="test_call_id_1",
            tool_call=tool_call_1,
            llm_response_id="response_1",
        ),
        ActionEvent(
            source="agent",
            thought=[TextContent(text="Test thought 2")],
            action=FinishAction(message="test2"),
            tool_name="finish",
            tool_call_id="test_call_id_2",
            tool_call=tool_call_2,
            llm_response_id="response_2",
        ),
    ]

    # Test that it returns UNKNOWN for all actions
    analyzed_actions = analyzer.analyze_pending_actions(action_events)

    assert len(analyzed_actions) == 2
    for action, risk in analyzed_actions:
        assert risk == SecurityRisk.UNKNOWN
        assert action in action_events


def test_default_analyzer_analyze_event():
    """Test that DefaultSecurityAnalyzer correctly handles analyze_event method."""
    analyzer = DefaultSecurityAnalyzer()

    # Create a mock action event
    tool_call = ChatCompletionMessageToolCall(
        id="test_call_id",
        type="function",
        function=Function(name="finish", arguments='{"message": "test"}'),
    )

    action_event = ActionEvent(
        source="agent",
        thought=[TextContent(text="Test thought")],
        action=FinishAction(message="test"),
        tool_name="finish",
        tool_call_id="test_call_id",
        tool_call=tool_call,
        llm_response_id="response_1",
    )

    # Test that it returns UNKNOWN for action events
    risk = analyzer.analyze_event(action_event)
    assert risk == SecurityRisk.UNKNOWN

    # Test that it returns None for non-action events
    message_event = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="Hello")]),
    )

    risk = analyzer.analyze_event(message_event)
    assert risk is None
