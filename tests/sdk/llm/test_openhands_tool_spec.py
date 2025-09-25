"""Tests for OpenHandsToolSpec and OpenHandsToolCall types."""

import json

from litellm.types.utils import ChatCompletionMessageToolCall

from openhands.sdk.llm.types import OpenHandsToolCall, OpenHandsToolSpec
from openhands.sdk.tool.tool import ToolAnnotations


def test_openhands_tool_spec_creation():
    """Test basic OpenHandsToolSpec creation."""
    spec = OpenHandsToolSpec(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {"arg": {"type": "string"}}},
    )

    assert spec.name == "test_tool"
    assert spec.description == "A test tool"
    assert spec.parameters == {
        "type": "object",
        "properties": {"arg": {"type": "string"}},
    }
    assert spec.annotations is None


def test_openhands_tool_spec_with_annotations():
    """Test OpenHandsToolSpec creation with annotations."""
    annotations = ToolAnnotations(
        title="A special tool",
        readOnlyHint=True,
        destructiveHint=False,
    )

    spec = OpenHandsToolSpec(
        name="readonly_tool",
        description="A tool that only reads data",
        parameters={"type": "object", "properties": {}},
        annotations=annotations,
    )

    assert spec.name == "readonly_tool"
    assert spec.annotations == annotations
    assert spec.annotations is not None
    assert spec.annotations.title == "A special tool"
    assert spec.annotations.readOnlyHint is True
    assert spec.annotations.destructiveHint is False


def test_openhands_tool_spec_to_litellm_format():
    """Test conversion to LiteLLM format."""
    spec = OpenHandsToolSpec(
        name="example_tool",
        description="An example tool for testing",
        parameters={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to process"}
            },
            "required": ["message"],
        },
    )

    litellm_format = spec.to_litellm_format()

    assert isinstance(litellm_format, dict)
    assert litellm_format["type"] == "function"
    function_chunk = litellm_format["function"]
    assert function_chunk["name"] == "example_tool"
    assert function_chunk.get("description") == "An example tool for testing"
    assert function_chunk.get("parameters") == spec.parameters


def test_openhands_tool_call_creation():
    """Test basic OpenHandsToolCall creation."""
    tool_call = OpenHandsToolCall(
        id="call_123",
        type="function",
        function={"name": "test_tool", "arguments": '{"arg": "value"}'},
    )

    assert tool_call.id == "call_123"
    assert tool_call.type == "function"
    assert tool_call.function["name"] == "test_tool"
    assert tool_call.function["arguments"] == '{"arg": "value"}'


def test_openhands_tool_call_from_litellm():
    """Test creation from LiteLLM tool call."""
    litellm_call = ChatCompletionMessageToolCall(
        id="call_456",
        type="function",
        function={"name": "example_tool", "arguments": '{"message": "hello"}'},
    )

    openhands_call = OpenHandsToolCall.from_litellm(litellm_call)

    assert openhands_call.id == "call_456"
    assert openhands_call.type == "function"
    assert openhands_call.function["name"] == "example_tool"
    assert openhands_call.function["arguments"] == '{"message": "hello"}'


def test_openhands_tool_call_to_litellm():
    """Test conversion to LiteLLM format."""
    openhands_call = OpenHandsToolCall(
        id="call_789",
        type="function",
        function={"name": "convert_tool", "arguments": '{"data": "test"}'},
    )

    litellm_call = openhands_call.to_litellm_format()

    assert isinstance(litellm_call, ChatCompletionMessageToolCall)
    assert litellm_call.id == "call_789"
    assert litellm_call.type == "function"
    assert litellm_call.function["name"] == "convert_tool"
    assert litellm_call.function["arguments"] == '{"data": "test"}'


def test_openhands_tool_spec_serialization():
    """Test that OpenHandsToolSpec can be serialized and deserialized."""
    original_spec = OpenHandsToolSpec(
        name="serialization_test",
        description="Testing serialization",
        parameters={"type": "object", "properties": {"test": {"type": "boolean"}}},
    )

    # Test JSON serialization
    json_data = original_spec.model_dump()
    reconstructed_spec = OpenHandsToolSpec(**json_data)

    assert reconstructed_spec.name == original_spec.name
    assert reconstructed_spec.description == original_spec.description
    assert reconstructed_spec.parameters == original_spec.parameters


def test_openhands_tool_call_serialization():
    """Test that OpenHandsToolCall can be serialized and deserialized."""
    original_call = OpenHandsToolCall(
        id="serialize_123",
        type="function",
        function={"name": "serialize_tool", "arguments": '{"serialize": true}'},
    )

    # Test JSON serialization
    json_data = original_call.model_dump()
    reconstructed_call = OpenHandsToolCall(**json_data)

    assert reconstructed_call.id == original_call.id
    assert reconstructed_call.type == original_call.type
    assert reconstructed_call.function == original_call.function


def test_openhands_types_are_mutable():
    """Test that OpenHands types can be modified (not frozen by default)."""
    spec = OpenHandsToolSpec(
        name="mutable_test",
        description="Testing mutability",
        parameters={"type": "object", "properties": {}},
    )

    tool_call = OpenHandsToolCall(
        id="mutable_call",
        type="function",
        function={"name": "mutable_tool", "arguments": "{}"},
    )

    # These should work since the models are not frozen
    spec.name = "modified_name"
    tool_call.id = "modified_id"

    assert spec.name == "modified_name"
    assert tool_call.id == "modified_id"


def test_complex_parameters_handling():
    """Test handling of complex parameter schemas."""
    complex_params = {
        "type": "object",
        "properties": {
            "nested_object": {
                "type": "object",
                "properties": {
                    "inner_field": {"type": "string"},
                    "inner_array": {
                        "type": "array",
                        "items": {"type": "number"},
                    },
                },
                "required": ["inner_field"],
            },
            "optional_enum": {
                "type": "string",
                "enum": ["option1", "option2", "option3"],
            },
        },
        "required": ["nested_object"],
    }

    spec = OpenHandsToolSpec(
        name="complex_tool",
        description="Tool with complex parameters",
        parameters=complex_params,
    )

    # Verify the complex parameters are preserved
    assert spec.parameters == complex_params

    # Verify conversion to LiteLLM preserves complexity
    litellm_format = spec.to_litellm_format()
    function_chunk = litellm_format["function"]
    assert function_chunk.get("parameters") == complex_params


def test_round_trip_conversion():
    """Test that conversions preserve data integrity."""
    # Create original LiteLLM tool call
    original_litellm = ChatCompletionMessageToolCall(
        id="round_trip_test",
        type="function",
        function={
            "name": "round_trip_tool",
            "arguments": json.dumps(
                {"complex": {"nested": "data", "array": [1, 2, 3]}}
            ),
        },
    )

    # Convert to OpenHands format
    openhands_call = OpenHandsToolCall.from_litellm(original_litellm)

    # Convert back to LiteLLM format
    converted_litellm = openhands_call.to_litellm_format()

    # Verify data integrity
    assert converted_litellm.id == original_litellm.id
    assert converted_litellm.type == original_litellm.type
    assert converted_litellm.function["name"] == original_litellm.function["name"]
    assert (
        converted_litellm.function["arguments"]
        == original_litellm.function["arguments"]
    )
