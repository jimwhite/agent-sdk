"""Test that Pydantic serialization warnings are fixed in integration test context."""

import warnings

from litellm.types.utils import Message as LiteLLMMessage

from openhands.sdk.event.llm_convertible.message import MessageEvent
from openhands.sdk.llm import Message


def test_integration_message_event_serialization():
    """Test that MessageEvent.llm_message.model_dump() doesn't produce Pydantic warnings."""  # noqa: E501
    # Create a properly initialized LiteLLM message (like what would come from real LLM)
    litellm_message = LiteLLMMessage(
        role="assistant",
        content="Test response content",
        tool_calls=None,
        function_call=None,
        refusal=None,
    )

    # Convert to SDK Message (this is what the LLM class does)
    sdk_message = Message.from_llm_chat_message(litellm_message)

    # Create MessageEvent with the SDK message (this is the correct type)
    message_event = MessageEvent(
        source="agent",
        llm_message=sdk_message,
    )

    # Capture warnings during model_dump() - this is what integration tests do
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # This is the exact line from base.py:100 that was causing warnings
        llm_message_dict = message_event.llm_message.model_dump()

        # Check that no Pydantic serialization warnings were generated
        pydantic_warnings = [
            warning
            for warning in w
            if "PydanticSerializationUnexpectedValue" in str(warning.message)
        ]

        assert len(pydantic_warnings) == 0, (
            f"Pydantic serialization warnings detected: "
            f"{[str(w.message) for w in pydantic_warnings]}"
        )

        # Verify the serialization worked correctly
        assert isinstance(llm_message_dict, dict)
        assert llm_message_dict["role"] == "assistant"
        assert len(llm_message_dict["content"]) == 1
        assert llm_message_dict["content"][0]["text"] == "Test response content"


def test_integration_conversation_callback_pattern():
    """Test the exact pattern used in BaseIntegrationTest.conversation_callback()."""
    # Create a properly initialized LiteLLM message
    litellm_message = LiteLLMMessage(
        role="assistant",
        content="Callback test response",
        tool_calls=None,
        function_call=None,
        refusal=None,
    )

    # Convert to SDK Message (this is what the LLM class does)
    sdk_message = Message.from_llm_chat_message(litellm_message)

    # Create MessageEvent with the SDK message
    event = MessageEvent(
        source="agent",
        llm_message=sdk_message,
    )

    # Simulate the exact pattern from BaseIntegrationTest.conversation_callback()
    llm_messages = []

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # This is the exact line from base.py:100
        llm_messages.append(event.llm_message.model_dump())

        # Check that no Pydantic serialization warnings were generated
        pydantic_warnings = [
            warning
            for warning in w
            if "PydanticSerializationUnexpectedValue" in str(warning.message)
        ]

        assert len(pydantic_warnings) == 0, (
            f"Integration callback pattern produced Pydantic warnings: "
            f"{[str(w.message) for w in pydantic_warnings]}"
        )

        # Verify the callback worked correctly
        assert len(llm_messages) == 1
        assert llm_messages[0]["role"] == "assistant"
        assert len(llm_messages[0]["content"]) == 1
        assert llm_messages[0]["content"][0]["text"] == "Callback test response"
