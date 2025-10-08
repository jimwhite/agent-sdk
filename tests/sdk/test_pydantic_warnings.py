"""Test to ensure no Pydantic serializer warnings are generated."""

import warnings

from openhands.sdk import Message
from tests.conftest import create_mock_litellm_response


def test_no_pydantic_warnings_on_message_serialization():
    """Test that Message.model_dump() doesn't generate Pydantic warnings."""
    # Set up warning capture
    collected_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        if "Pydantic serializer warnings" in str(message):
            collected_warnings.append(str(message))

    # Capture warnings
    original_showwarning = warnings.showwarning
    warnings.showwarning = warning_handler

    try:
        # Create a mock LiteLLM response using the conftest function
        mock_response = create_mock_litellm_response(
            content="Test message content",
            response_id="test-123",
            model="claude-3-5-sonnet-20241022",
        )

        # Create a Message from the LiteLLM response
        message = Message.from_llm_chat_message(mock_response.choices[0].message)  # type: ignore[attr-defined]

        # Serialize the message - this should not generate warnings
        serialized = message.model_dump()

        # Verify serialization worked
        assert serialized["role"] == "assistant"
        # Content is a list of TextContent objects
        assert len(serialized["content"]) == 1
        assert serialized["content"][0]["text"] == "Test message content"

        # Verify no Pydantic warnings were generated
        assert len(collected_warnings) == 0, (
            f"Pydantic warnings were generated: {collected_warnings}"
        )

    finally:
        # Restore original warning handler
        warnings.showwarning = original_showwarning


def test_integration_pattern_no_warnings():
    """Test the exact pattern used in integration tests: event.llm_message.model_dump()."""  # noqa: E501
    from openhands.sdk.event.llm_convertible.message import MessageEvent

    # Set up warning capture
    collected_warnings = []

    def warning_handler(message, category, filename, lineno, file=None, line=None):
        if "Pydantic serializer warnings" in str(message):
            collected_warnings.append(str(message))

    # Capture warnings
    original_showwarning = warnings.showwarning
    warnings.showwarning = warning_handler

    try:
        # Create a mock LiteLLM response using the conftest function
        mock_response = create_mock_litellm_response(
            content="Test integration content",
            response_id="test-integration",
            model="claude-3-5-sonnet-20241022",
        )

        # Create a MessageEvent with the mock response (simulating integration test)
        openhands_message = Message.from_llm_chat_message(
            mock_response.choices[0].message  # type: ignore[attr-defined]
        )
        MessageEvent(
            source="agent",
            llm_message=openhands_message,
        )

        # This is the exact pattern from integration tests that was causing warnings
        # The integration tests call model_dump() on the raw LiteLLM message
        serialized = mock_response.choices[0].message.model_dump()  # type: ignore[attr-defined]

        # Verify serialization worked
        assert "content" in serialized
        assert "role" in serialized
        assert serialized["role"] == "assistant"

        # Verify no Pydantic warnings were generated
        assert len(collected_warnings) == 0, (
            f"Pydantic warnings were generated: {collected_warnings}"
        )

    finally:
        # Restore original warning handler
        warnings.showwarning = original_showwarning
