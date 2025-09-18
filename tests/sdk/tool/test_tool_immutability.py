"""Tests for the Tool class in openhands.sdk.runtime.tool."""

from typing import Dict, List

import pytest
from pydantic import ValidationError

from openhands.sdk.tool import (
    Schema,
    SchemaField,
    SchemaFieldType,
    SchemaInstance,
    Tool,
    ToolAnnotations,
    ToolExecutor,
)


MOCK_ACTION_SCHEMA_NAME = "tests.mockAction.action"
MOCK_OBSERVATION_SCHEMA_NAME = "tests.mockObservation.observation"
MOCK_ACTION_INSTANCE_NAME = "mockAction"
MOCK_OBSERVATION_INSTANCE_NAME = "mockObservation"


def create_mock_action_schema() -> Schema:
    """Create mock action schema for testing."""
    return Schema(
        name=MOCK_ACTION_SCHEMA_NAME,
        fields=[
            SchemaField(
                name="command",
                type=SchemaFieldType.from_type(str),
                description="Command to execute",
                required=True,
            ),
            SchemaField(
                name="optional_field",
                type=SchemaFieldType.from_type(str),
                description="Optional field",
                required=False,
            ),
            SchemaField(
                name="nested",
                type=SchemaFieldType.from_type(Dict[str, str]),
                description="Nested object",
                required=False,
            ),
            SchemaField(
                name="array_field",
                type=SchemaFieldType.from_type(List[str]),
                description="Array field",
                required=False,
            ),
        ],
    )


def create_mock_observation_schema() -> Schema:
    """Create mock observation schema for testing."""
    return Schema(
        name=MOCK_OBSERVATION_SCHEMA_NAME,
        fields=[
            SchemaField(
                name="result",
                type=SchemaFieldType.from_type(str),
                description="Result of the action",
                required=True,
            ),
            SchemaField(
                name="extra_field",
                type=SchemaFieldType.from_type(str),
                description="Extra field",
                required=False,
            ),
        ],
    )


def create_mock_action(**kwargs) -> SchemaInstance:
    """Create mock action instance."""
    data = {
        "command": "test",
        "optional_field": None,
        "nested": {},
        "array_field": [],
        **kwargs,
    }
    return SchemaInstance(
        name=MOCK_ACTION_INSTANCE_NAME,
        definition=create_mock_action_schema(),
        data=data,
    )


def create_mock_observation(**kwargs) -> SchemaInstance:
    """Create mock observation instance."""
    data = {"result": "success", "extra_field": None, **kwargs}
    return SchemaInstance(
        name=MOCK_OBSERVATION_INSTANCE_NAME,
        definition=create_mock_observation_schema(),
        data=data,
    )


class TestToolImmutability:
    """Test suite for Tool immutability features."""

    def test_tool_is_frozen(self):
        """Test that Tool instances are frozen and cannot be modified."""
        tool = Tool(
            name="test_tool",
            description="Test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        # Test that we cannot modify any field
        with pytest.raises(
            Exception
        ):  # Pydantic raises ValidationError for frozen models
            tool.name = "modified_name"

        with pytest.raises(Exception):
            tool.description = "modified_description"

        with pytest.raises(Exception):
            tool.executor = None

    def test_tool_set_executor_returns_new_instance(self):
        """Test that set_executor returns a new Tool instance."""
        tool = Tool(
            name="test_tool",
            description="Test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        class NewExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_mock_observation(result="new_result")

        new_executor = NewExecutor()
        new_tool = tool.set_executor(new_executor)

        # Verify that a new instance was created
        assert new_tool is not tool
        assert tool.executor is None
        assert new_tool.executor is new_executor
        assert new_tool.name == tool.name
        assert new_tool.description == tool.description

    def test_tool_model_copy_creates_modified_instance(self):
        """Test that model_copy can create modified versions of Tool instances."""
        tool = Tool(
            name="test_tool",
            description="Test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        # Create a copy with modified fields
        modified_tool = tool.model_copy(
            update={"name": "modified_tool", "description": "Modified description"}
        )

        # Verify that a new instance was created with modifications
        assert modified_tool is not tool
        assert tool.name == "test_tool"
        assert tool.description == "Test tool"
        assert modified_tool.name == "modified_tool"
        assert modified_tool.description == "Modified description"

    def test_tool_meta_field_immutability(self):
        """Test that the meta field works correctly and is immutable."""
        meta_data = {"version": "1.0", "author": "test"}
        tool = Tool(
            name="test_tool",
            description="Test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            meta=meta_data,
        )

        # Verify meta field is accessible
        assert tool.meta == meta_data

        # Test that meta field cannot be directly modified
        with pytest.raises(Exception):
            tool.meta = {"version": "2.0"}

        # Test that meta field can be modified via model_copy
        new_meta = {"version": "2.0", "author": "new_author"}
        modified_tool = tool.model_copy(update={"meta": new_meta})
        assert modified_tool.meta == new_meta
        assert tool.meta == meta_data  # Original unchanged

    def test_tool_constructor_parameter_validation(self):
        """Test that Tool constructor validates parameters correctly."""
        # Test that new parameter names work
        tool = Tool(
            name="test_tool",
            description="Test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )
        assert tool.input_schema.name == MOCK_ACTION_SCHEMA_NAME
        assert tool.output_schema is not None
        assert tool.output_schema.name == MOCK_OBSERVATION_SCHEMA_NAME

        # Test that invalid field types are rejected
        with pytest.raises(ValidationError):
            Tool(
                name="test_tool",
                description="Test tool",
                input_schema="invalid_type",  # type: ignore[arg-type] # Should be Schema, not string
                output_schema=create_mock_observation_schema(),
            )

    def test_tool_annotations_immutability(self):
        """Test that ToolAnnotations are also immutable when part of Tool."""
        annotations = ToolAnnotations(
            title="Test Tool",
            readOnlyHint=True,
            destructiveHint=False,
        )

        tool = Tool(
            name="test_tool",
            description="Test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            annotations=annotations,
        )

        # Test that annotations field cannot be reassigned (frozen behavior)
        with pytest.raises(Exception):
            tool.annotations = ToolAnnotations(title="New Annotations")

        # Test that annotations can be modified via model_copy
        new_annotations = ToolAnnotations(
            title="Modified Tool",
            readOnlyHint=False,
            destructiveHint=True,
        )
        modified_tool = tool.model_copy(update={"annotations": new_annotations})
        assert (
            modified_tool.annotations
            and modified_tool.annotations.title == "Modified Tool"
        )
        assert (
            tool.annotations and tool.annotations.title == "Test Tool"
        )  # Original unchanged
