"""Test that our auto-callback system works correctly."""

from unittest.mock import Mock

from openhands.sdk.conversation.context import (
    clear_conversation_context,
    set_conversation_context,
)
from openhands.sdk.event.llm_convertible import MessageEvent
from openhands.sdk.llm import Message, TextContent


def test_auto_callback_system():
    """Test that events automatically trigger callbacks when created."""
    # Create a mock callback
    mock_callback = Mock()

    # Set up conversation context
    set_conversation_context(mock_callback)

    try:
        # Create an event - this should automatically trigger the callback
        message = Message(role="user", content=[TextContent(text="test")])
        event = MessageEvent(source="user", llm_message=message)

        # Verify the callback was called with the event
        mock_callback.assert_called_once_with(event)

    finally:
        # Clean up context
        clear_conversation_context()


def test_no_callback_without_context():
    """Test that events don't trigger callbacks when no context is set."""
    # Clear any existing context
    clear_conversation_context()

    # Create a mock that should NOT be called
    mock_callback = Mock()

    # Create an event without setting context
    message = Message(role="user", content=[TextContent(text="test")])
    _ = MessageEvent(source="user", llm_message=message)

    # Verify the callback was NOT called
    mock_callback.assert_not_called()
