"""Tests for proper handling of empty FinishAction messages in business logic layer."""

from litellm.types.utils import ChatCompletionMessageToolCall, Function

from openhands.sdk.event.base import _combine_action_events
from openhands.sdk.event.llm_convertible import ActionEvent
from openhands.sdk.llm.message import TextContent
from openhands.sdk.tool.builtins import FinishAction


def test_action_event_empty_finish_action_to_llm_message():
    """Test that ActionEvent with empty FinishAction gets default content."""
    # Create a FinishAction with empty message
    finish_action = FinishAction(message="")

    # Create tool call for the action
    tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(name="finish", arguments='{"message": ""}'),
    )

    # Create ActionEvent with empty thought
    action_event = ActionEvent(
        thought=[],  # Empty thought
        action=finish_action,
        tool_name="finish",
        tool_call_id="call_123",
        tool_call=tool_call,
        llm_response_id="response_123",
    )

    # Convert to LLM message
    message = action_event.to_llm_message()

    # Should have default content for empty FinishAction
    assert message.role == "assistant"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    assert message.content[0].text == "Task completed."


def test_action_event_empty_text_finish_action_to_llm_message():
    """Test that ActionEvent with FinishAction and empty text thought gets default."""
    # Create a FinishAction
    finish_action = FinishAction(message="Task is done")

    # Create tool call for the action
    tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(name="finish", arguments='{"message": "Task is done"}'),
    )

    # Create ActionEvent with empty text thought
    action_event = ActionEvent(
        thought=[TextContent(text="")],  # Empty text thought
        action=finish_action,
        tool_name="finish",
        tool_call_id="call_123",
        tool_call=tool_call,
        llm_response_id="response_123",
    )

    # Convert to LLM message
    message = action_event.to_llm_message()

    # Should have default content for empty FinishAction thought
    assert message.role == "assistant"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    assert message.content[0].text == "Task completed."


def test_action_event_whitespace_finish_action_to_llm_message():
    """Test that ActionEvent with FinishAction and whitespace-only gets default."""
    # Create a FinishAction
    finish_action = FinishAction(message="Task is done")

    # Create tool call for the action
    tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(name="finish", arguments='{"message": "Task is done"}'),
    )

    # Create ActionEvent with whitespace-only thought
    action_event = ActionEvent(
        thought=[TextContent(text="   \n\t  ")],  # Whitespace-only thought
        action=finish_action,
        tool_name="finish",
        tool_call_id="call_123",
        tool_call=tool_call,
        llm_response_id="response_123",
    )

    # Convert to LLM message
    message = action_event.to_llm_message()

    # Should have default content for whitespace-only FinishAction thought
    assert message.role == "assistant"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    assert message.content[0].text == "Task completed."


def test_action_event_non_empty_finish_action_unchanged():
    """Test that ActionEvent with non-empty FinishAction thought is unchanged."""
    # Create a FinishAction
    finish_action = FinishAction(message="Task is done")

    # Create tool call for the action
    tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(name="finish", arguments='{"message": "Task is done"}'),
    )

    # Create ActionEvent with non-empty thought
    action_event = ActionEvent(
        thought=[TextContent(text="I have completed the task successfully.")],
        action=finish_action,
        tool_name="finish",
        tool_call_id="call_123",
        tool_call=tool_call,
        llm_response_id="response_123",
    )

    # Convert to LLM message
    message = action_event.to_llm_message()

    # Should preserve original content
    assert message.role == "assistant"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    assert message.content[0].text == "I have completed the task successfully."


def test_action_event_non_finish_action_unchanged():
    """Test that ActionEvent with non-FinishAction is unchanged even with empty."""
    # Import a different action type for testing
    from openhands.sdk.tool.builtins import ThinkAction

    # Create a non-FinishAction
    think_action = ThinkAction(thought="")

    # Create tool call for the action
    tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(name="think", arguments='{"thought": ""}'),
    )

    # Create ActionEvent with empty thought
    action_event = ActionEvent(
        thought=[],  # Empty thought
        action=think_action,
        tool_name="think",
        tool_call_id="call_123",
        tool_call=tool_call,
        llm_response_id="response_123",
    )

    # Convert to LLM message
    message = action_event.to_llm_message()

    # Should NOT get default content for non-FinishAction
    assert message.role == "assistant"
    assert len(message.content) == 0  # Should remain empty


def test_combine_action_events_with_empty_finish_action():
    """Test that _combine_action_events handles empty FinishAction correctly."""
    # Create a FinishAction with empty message
    finish_action = FinishAction(message="")

    # Create tool call for the action
    tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(name="finish", arguments='{"message": ""}'),
    )

    # Create ActionEvent with empty thought
    action_event = ActionEvent(
        thought=[],  # Empty thought
        action=finish_action,
        tool_name="finish",
        tool_call_id="call_123",
        tool_call=tool_call,
        llm_response_id="response_123",
    )

    # Combine events (single event case)
    message = _combine_action_events([action_event])

    # Should have default content for empty FinishAction
    assert message.role == "assistant"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    assert message.content[0].text == "Task completed."


def test_combine_action_events_multi_action_with_finish():
    """Test that _combine_action_events handles multi-action batch with FinishAction."""
    # Create a FinishAction
    finish_action = FinishAction(message="Done")

    # Create another action (using ThinkAction as example)
    from openhands.sdk.tool.builtins import ThinkAction

    think_action = ThinkAction(thought="Thinking...")

    # Create tool calls
    finish_tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(name="finish", arguments='{"message": "Done"}'),
    )

    think_tool_call = ChatCompletionMessageToolCall(
        id="call_124",
        type="function",
        function=Function(name="think", arguments='{"thought": "Thinking..."}'),
    )

    # Create ActionEvents - first with empty thought, second with empty thought
    finish_event = ActionEvent(
        thought=[],  # Empty thought in first event
        action=finish_action,
        tool_name="finish",
        tool_call_id="call_123",
        tool_call=finish_tool_call,
        llm_response_id="response_123",
    )

    think_event = ActionEvent(
        thought=[],  # Empty thought in second event (as expected for multi-action)
        action=think_action,
        tool_name="think",
        tool_call_id="call_124",
        tool_call=think_tool_call,
        llm_response_id="response_123",
    )

    # Combine events (multi-action case)
    message = _combine_action_events([finish_event, think_event])

    # Should have default content because one action is FinishAction with empty thought
    assert message.role == "assistant"
    assert len(message.content) == 1
    assert isinstance(message.content[0], TextContent)
    assert message.content[0].text == "Task completed."
    assert len(message.tool_calls) == 2  # Should have both tool calls
