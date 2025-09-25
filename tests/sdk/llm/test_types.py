"""Tests for OpenHands-native LLM types."""

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function

from openhands.sdk.llm.types import OpenHandsToolCall, OpenHandsToolSpec


def test_openhands_tool_call_from_litellm():
    """Test OpenHandsToolCall.from_litellm() conversion."""
    litellm_tool_call = ChatCompletionMessageToolCall(
        id="call_123",
        type="function",
        function=Function(
            name="test_function", arguments='{"param1": "value1", "param2": 42}'
        ),
    )

    openhands_tool_call = OpenHandsToolCall.from_litellm(litellm_tool_call)

    assert openhands_tool_call.id == "call_123"
    assert openhands_tool_call.type == "function"
    assert openhands_tool_call.function["name"] == "test_function"
    assert (
        openhands_tool_call.function["arguments"]
        == '{"param1": "value1", "param2": 42}'
    )


def test_openhands_tool_call_to_litellm_format():
    """Test OpenHandsToolCall.to_litellm_format() conversion."""
    openhands_tool_call = OpenHandsToolCall(
        id="call_456",
        type="function",
        function={"name": "another_function", "arguments": '{"test": true}'},
    )

    litellm_tool_call = openhands_tool_call.to_litellm_format()

    assert litellm_tool_call.id == "call_456"
    assert litellm_tool_call.type == "function"
    assert litellm_tool_call.function.name == "another_function"
    assert litellm_tool_call.function.arguments == '{"test": true}'


def test_openhands_tool_call_round_trip():
    """Test round-trip conversion between LiteLLM and OpenHands formats."""
    original_litellm = ChatCompletionMessageToolCall(
        id="call_round_trip",
        type="function",
        function=Function(name="round_trip_function", arguments='{"data": [1, 2, 3]}'),
    )

    # Convert to OpenHands format and back
    openhands_format = OpenHandsToolCall.from_litellm(original_litellm)
    back_to_litellm = openhands_format.to_litellm_format()

    # Verify round-trip preservation
    assert back_to_litellm.id == original_litellm.id
    assert back_to_litellm.type == original_litellm.type
    assert back_to_litellm.function.name == original_litellm.function.name
    assert back_to_litellm.function.arguments == original_litellm.function.arguments


def test_openhands_tool_spec_to_litellm_format():
    """Test OpenHandsToolSpec.to_litellm_format() conversion."""
    tool_spec = OpenHandsToolSpec(
        name="test_tool",
        description="A test tool for validation",
        parameters={
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "First parameter"},
                "param2": {"type": "integer", "description": "Second parameter"},
            },
            "required": ["param1"],
        },
    )

    litellm_format = tool_spec.to_litellm_format()

    assert litellm_format["type"] == "function"
    function_spec = litellm_format["function"]
    assert function_spec["name"] == "test_tool"
    assert function_spec.get("description") == "A test tool for validation"

    parameters = function_spec.get("parameters", {})
    assert parameters.get("type") == "object"
    properties = parameters.get("properties", {})
    assert "param1" in properties
    assert "param2" in properties
    assert parameters.get("required") == ["param1"]


def test_openhands_tool_spec_with_annotations():
    """Test OpenHandsToolSpec with tool annotations."""
    from openhands.sdk.tool.tool import ToolAnnotations

    annotations = ToolAnnotations(readOnlyHint=True, destructiveHint=False)

    tool_spec = OpenHandsToolSpec(
        name="read_only_tool",
        description="A read-only tool",
        parameters={"type": "object", "properties": {}},
        annotations=annotations,
    )

    assert tool_spec.annotations is not None
    assert tool_spec.annotations.readOnlyHint is True
    assert tool_spec.annotations.destructiveHint is False

    # Verify it converts to LiteLLM format correctly
    litellm_format = tool_spec.to_litellm_format()
    function_spec = litellm_format["function"]
    assert function_spec["name"] == "read_only_tool"
