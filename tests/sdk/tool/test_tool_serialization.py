"""Test tool JSON serialization without discriminated unions.

Tools now persist raw JSON schemas for inputs/outputs and reconstruct runtime
Pydantic models on demand. There is no 'kind' discriminator.
"""

import json

from pydantic import BaseModel

from openhands.sdk.tool import Tool, ToolType
from openhands.sdk.tool.builtins import FinishTool, ThinkTool


def test_tool_serialization_deserialization() -> None:
    """Test that Tool supports polymorphic JSON serialization/deserialization."""
    # Use FinishTool which is a simple built-in tool
    tool = FinishTool

    # Serialize to JSON
    tool_json = tool.model_dump_json()

    # Deserialize from JSON using the base class
    deserialized_tool = Tool.model_validate_json(tool_json)

    # Should deserialize to the correct type with same serializable data
    assert isinstance(deserialized_tool, Tool)
    assert tool.model_dump() == deserialized_tool.model_dump()


def test_tool_supports_polymorphic_field_json_serialization() -> None:
    """Test that Tool supports polymorphic JSON serialization when used as a field."""

    class Container(BaseModel):
        tool: Tool

    # Create container with tool
    tool = FinishTool
    container = Container(tool=tool)

    # Serialize to JSON
    container_json = container.model_dump_json()

    # Deserialize from JSON
    deserialized_container = Container.model_validate_json(container_json)

    # Should preserve the tool type with same serializable data
    assert isinstance(deserialized_container.tool, Tool)
    assert tool.model_dump() == deserialized_container.tool.model_dump()


def test_tool_supports_nested_polymorphic_json_serialization() -> None:
    """Test that Tool supports nested polymorphic JSON serialization."""

    class NestedContainer(BaseModel):
        tools: list[Tool]

    # Create container with multiple tools
    tool1 = FinishTool
    tool2 = ThinkTool
    container = NestedContainer(tools=[tool1, tool2])

    # Serialize to JSON
    container_json = container.model_dump_json()

    # Deserialize from JSON
    deserialized_container = NestedContainer.model_validate_json(container_json)

    # Should preserve all tool types with same serializable data
    assert len(deserialized_container.tools) == 2
    assert isinstance(deserialized_container.tools[0], Tool)
    assert isinstance(deserialized_container.tools[1], Tool)
    assert tool1.model_dump() == deserialized_container.tools[0].model_dump()
    assert tool2.model_dump() == deserialized_container.tools[1].model_dump()


def test_tool_model_validate_json_dict() -> None:
    """Test that Tool.model_validate works with dict from JSON."""
    # Create tool
    tool = FinishTool

    # Serialize to JSON, then parse to dict
    tool_json = tool.model_dump_json()
    tool_dict = json.loads(tool_json)

    # Deserialize from dict
    deserialized_tool = Tool.model_validate(tool_dict)

    # Should have same serializable data
    assert isinstance(deserialized_tool, Tool)
    assert tool.model_dump() == deserialized_tool.model_dump()


def test_tool_fallback_behavior_json() -> None:
    """Tool can be reconstructed from JSON schema without type strings."""
    tool_dict = {
        "name": "schema-tool",
        "description": "A schema-first test tool",
        "input_schema": {
            "type": "object",
            "properties": {"message": {"type": "string"}},
            "required": ["message"],
        },
    }
    tool_json = json.dumps(tool_dict)

    deserialized_tool = Tool.model_validate_json(tool_json)
    assert isinstance(deserialized_tool, Tool)
    assert deserialized_tool.name == "schema-tool"
    assert deserialized_tool.description == "A schema-first test tool"
    # Action type should be reconstructed at runtime
    assert deserialized_tool.action_type is not None


def test_tool_type_annotation_works_json() -> None:
    """Test that ToolType annotation works correctly with JSON."""
    # Create tool
    tool = FinishTool

    # Use ToolType annotation
    class TestModel(BaseModel):
        tool: ToolType

    model = TestModel(tool=tool)

    # Serialize to JSON
    model_json = model.model_dump_json()

    # Deserialize from JSON
    deserialized_model = TestModel.model_validate_json(model_json)

    # Should work correctly with same serializable data
    assert isinstance(deserialized_model.tool, Tool)
    assert tool.model_dump() == deserialized_model.tool.model_dump()


def test_tool_to_openai_tool_has_parameters() -> None:
    tool = FinishTool
    oai = tool.to_openai_tool()
    assert oai["type"] == "function"
    fn = oai["function"]
    assert fn["name"] == tool.name
    # parameters isn't a required key, but should be present as a dict here
    assert isinstance(fn.get("parameters", {}), dict)
