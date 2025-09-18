"""Test cases for the Tool class using new schema system."""

from typing import Dict, List

import pytest

from openhands.sdk.tool import (
    Schema,
    SchemaField,
    SchemaFieldType,
    SchemaInstance,
    Tool,
    ToolAnnotations,
    ToolExecutor,
)


def create_mock_action_schema() -> Schema:
    """Create mock action schema for testing."""
    return Schema(
        name="MockAction",
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
                type=SchemaFieldType.from_type(List[int]),
                description="Array field",
                required=False,
            ),
        ],
    )


def create_mock_observation_schema() -> Schema:
    """Create mock observation schema for testing."""
    return Schema(
        name="MockObservation",
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
    }
    data.update(kwargs)
    schema = create_mock_action_schema()
    return SchemaInstance(name=schema.name, definition=schema, data=data)


def create_mock_observation(**kwargs) -> SchemaInstance:
    """Create mock observation instance."""
    data = {
        "result": "success",
        "extra_field": None,
    }
    data.update(kwargs)
    schema = create_mock_observation_schema()
    return SchemaInstance(name=schema.name, definition=schema, data=data)


class TestTool:
    """Test cases for the Tool class."""

    def test_tool_creation_basic(self):
        """Test basic tool creation."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema.name == "MockAction"
        assert tool.output_schema is not None
        assert tool.output_schema.name == "MockObservation"
        assert tool.executor is None

    def test_tool_creation_with_executor(self):
        """Test tool creation with executor function."""

        class MockExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_mock_observation(
                    result=f"Executed: {action.data['command']}"
                )

        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            executor=MockExecutor(),
        )

        assert tool.executor is not None
        action = create_mock_action(command="test")
        result = tool.call(action)
        assert isinstance(result, SchemaInstance)
        assert result.data["result"] == "Executed: test"

    def test_tool_creation_with_annotations(self):
        """Test tool creation with annotations."""
        annotations = ToolAnnotations(
            title="Annotated Tool",
            readOnlyHint=True,
            destructiveHint=False,
        )

        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            annotations=annotations,
        )

        assert tool.annotations is not None
        assert tool.annotations == annotations
        assert tool.annotations.title == "Annotated Tool"
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False

    def test_to_mcp_tool_basic(self):
        """Test conversion to MCP tool format."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        mcp_tool = tool.to_mcp_tool()

        assert mcp_tool["name"] == "test_tool"
        assert mcp_tool["description"] == "A test tool"
        assert "inputSchema" in mcp_tool
        assert mcp_tool["inputSchema"]["type"] == "object"
        assert "properties" in mcp_tool["inputSchema"]

        # Check that action fields are in the schema
        properties = mcp_tool["inputSchema"]["properties"]
        assert "command" in properties
        assert "optional_field" in properties
        assert "nested" in properties
        assert "array_field" in properties

    def test_to_mcp_tool_with_annotations(self):
        """Test MCP tool conversion with annotations."""
        annotations = ToolAnnotations(
            title="Custom Tool",
            readOnlyHint=True,
        )

        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            annotations=annotations,
        )

        mcp_tool = tool.to_mcp_tool()

        # Tool should include annotations
        assert mcp_tool["name"] == "test_tool"
        assert mcp_tool["description"] == "A test tool"
        assert "annotations" in mcp_tool
        assert mcp_tool["annotations"] == annotations

    def test_call_without_executor(self):
        """Test calling tool without executor raises error."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        action = create_mock_action(command="test")
        with pytest.raises(
            NotImplementedError, match="Tool 'test_tool' has no executor"
        ):
            tool.call(action)

    def test_call_with_executor(self):
        """Test calling tool with executor."""

        class MockExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_mock_observation(
                    result=f"Processed: {action.data['command']}"
                )

        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            executor=MockExecutor(),
        )

        action = create_mock_action(command="test_command")
        result = tool.call(action)

        assert isinstance(result, SchemaInstance)
        assert result.data["result"] == "Processed: test_command"

    def test_schema_generation_complex_types(self):
        """Test schema generation with complex field types."""

        def create_complex_action_schema() -> Schema:
            return Schema(
                name="ComplexAction",
                fields=[
                    SchemaField(
                        name="simple_field",
                        type=SchemaFieldType.from_type(str),
                        description="Simple string field",
                        required=True,
                    ),
                    SchemaField(
                        name="optional_int",
                        type=SchemaFieldType.from_type(int),
                        description="Optional integer",
                        required=False,
                    ),
                    SchemaField(
                        name="string_list",
                        type=SchemaFieldType.from_type(List[str]),
                        description="List of strings",
                        required=False,
                    ),
                ],
            )

        tool = Tool(
            name="complex_tool",
            description="Tool with complex types",
            input_schema=create_complex_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        mcp_tool = tool.to_mcp_tool()
        properties = mcp_tool["inputSchema"]["properties"]
        assert "simple_field" in properties
        assert properties["simple_field"]["type"] == "string"
        assert "optional_int" in properties
        assert properties["optional_int"]["type"] == "integer"
        assert "string_list" in properties
        assert properties["string_list"]["type"] == "array"
        assert properties["string_list"]["items"]["type"] == "string"

    def test_observation_type_validation(self):
        """Test that observation type is properly validated."""

        class MockExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_mock_observation(result="success")

        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            executor=MockExecutor(),
        )

        action = create_mock_action(command="test")
        result = tool.call(action)

        # Should return the correct observation type
        assert isinstance(result, SchemaInstance)
        assert result.data["result"] == "success"

    def test_observation_with_extra_fields(self):
        """Test observation with additional fields."""

        class MockExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_mock_observation(result="test", extra_field="extra_data")

        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            executor=MockExecutor(),
        )

        action = create_mock_action(command="test")
        result = tool.call(action)

        assert isinstance(result, SchemaInstance)
        assert result.data["result"] == "test"
        assert result.data["extra_field"] == "extra_data"

    def test_action_validation_with_nested_data(self):
        """Test action validation with nested data structures."""
        # Create action with nested data
        action = create_mock_action(
            command="test",
            nested={"value": "test"},
            array_field=[1, 2, 3],
        )

        assert isinstance(action, SchemaInstance)
        assert action.data["nested"] == {"value": "test"}
        assert action.data["array_field"] == [1, 2, 3]
        assert "optional_field" in action.data

    def test_tool_with_no_observation_type(self):
        """Test tool creation with None observation type."""
        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=None,
        )

        assert tool.output_schema is None

        # Should still be able to create MCP tool
        mcp_tool = tool.to_mcp_tool()
        assert mcp_tool["name"] == "test_tool"

    def test_executor_function_attachment(self):
        """Test creating tool with executor."""

        # Create executor first
        class MockExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_mock_observation(
                    result=f"Attached: {action.data['command']}"
                )

        executor = MockExecutor()

        tool = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            executor=executor,
        )

        # Should have executor
        assert tool.executor is not None

        # Should work
        action = create_mock_action(command="test")
        result = tool.call(action)
        assert isinstance(result, SchemaInstance)
        assert result.data["result"] == "Attached: test"

    def test_tool_name_validation(self):
        """Test tool name validation."""
        # Valid names should work
        tool = Tool(
            name="valid_tool_name",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )
        assert tool.name == "valid_tool_name"

        # Empty name should still work (validation might be elsewhere)
        tool2 = Tool(
            name="",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )
        assert tool2.name == ""

    def test_complex_executor_return_types(self):
        """Test executor with complex return types."""

        def create_complex_observation_schema() -> Schema:
            return Schema(
                name="ComplexObservation",
                fields=[
                    SchemaField(
                        name="data",
                        type=SchemaFieldType.from_type(Dict[str, str]),
                        description="Complex data",
                        required=False,
                    ),
                    SchemaField(
                        name="count",
                        type=SchemaFieldType.from_type(int),
                        description="Count field",
                        required=False,
                    ),
                ],
            )

        def create_complex_observation(**kwargs) -> SchemaInstance:
            data = {
                "data": {},
                "count": 0,
            }
            data.update(kwargs)
            schema = create_complex_observation_schema()
            return SchemaInstance(name=schema.name, definition=schema, data=data)

        class MockComplexExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_complex_observation(
                    data={"processed": action.data["command"], "timestamp": "12345"},
                    count=len(action.data["command"])
                    if action.data.get("command")
                    else 0,
                )

        tool = Tool(
            name="complex_tool",
            description="Tool with complex observation",
            input_schema=create_mock_action_schema(),
            output_schema=create_complex_observation_schema(),
            executor=MockComplexExecutor(),
        )

        action = create_mock_action(command="test_command")
        result = tool.call(action)

        assert isinstance(result, SchemaInstance)
        assert result.data["data"]["processed"] == "test_command"
        assert result.data["count"] == len("test_command")

    def test_error_handling_in_executor(self):
        """Test error handling when executor raises exceptions."""

        class FailingExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                raise RuntimeError("Executor failed")

        tool = Tool(
            name="failing_tool",
            description="Tool that fails",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            executor=FailingExecutor(),
        )

        action = create_mock_action(command="test")
        with pytest.raises(RuntimeError, match="Executor failed"):
            tool.call(action)

    def test_executor_with_observation_validation(self):
        """Test that executor return values are validated."""

        def create_strict_observation_schema() -> Schema:
            return Schema(
                name="StrictObservation",
                fields=[
                    SchemaField(
                        name="message",
                        type=SchemaFieldType.from_type(str),
                        description="Required message field",
                        required=True,
                    ),
                    SchemaField(
                        name="value",
                        type=SchemaFieldType.from_type(int),
                        description="Required value field",
                        required=True,
                    ),
                ],
            )

        def create_strict_observation(**kwargs) -> SchemaInstance:
            data = {
                "message": "success",
                "value": 42,
            }
            data.update(kwargs)
            schema = create_strict_observation_schema()
            return SchemaInstance(name=schema.name, definition=schema, data=data)

        class ValidExecutor(ToolExecutor):
            def __call__(self, action: SchemaInstance) -> SchemaInstance:
                return create_strict_observation(message="success", value=42)

        tool = Tool(
            name="strict_tool",
            description="Tool with strict observation",
            input_schema=create_mock_action_schema(),
            output_schema=create_strict_observation_schema(),
            executor=ValidExecutor(),
        )

        action = create_mock_action(command="test")
        result = tool.call(action)
        assert isinstance(result, SchemaInstance)
        assert result.data["message"] == "success"
        assert result.data["value"] == 42

    def test_tool_equality_and_hashing(self):
        """Test tool equality and hashing behavior."""
        tool1 = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        tool2 = Tool(
            name="test_tool",
            description="A test tool",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        # Tools with same parameters should be equal
        assert tool1.name == tool2.name
        assert tool1.description == tool2.description
        assert tool1.input_schema.name == tool2.input_schema.name

    def test_mcp_tool_schema_required_fields(self):
        """Test that MCP tool schema includes required fields."""

        def create_required_field_action_schema() -> Schema:
            return Schema(
                name="RequiredFieldAction",
                fields=[
                    SchemaField(
                        name="required_field",
                        type=SchemaFieldType.from_type(str),
                        description="This field is required",
                        required=True,
                    ),
                    SchemaField(
                        name="optional_field",
                        type=SchemaFieldType.from_type(str),
                        description="This field is optional",
                        required=False,
                    ),
                ],
            )

        tool = Tool(
            name="required_tool",
            description="Tool with required fields",
            input_schema=create_required_field_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        mcp_tool = tool.to_mcp_tool()
        schema = mcp_tool["inputSchema"]

        # Check that required fields are marked as required
        assert "required" in schema
        assert "required_field" in schema["required"]
        assert "optional_field" not in schema["required"]

    def test_tool_with_meta_data(self):
        """Test tool creation with metadata."""
        meta_data = {"version": "1.0", "author": "test"}

        tool = Tool(
            name="meta_tool",
            description="Tool with metadata",
            input_schema=create_mock_action_schema(),
            output_schema=create_mock_observation_schema(),
            meta=meta_data,
        )

        assert tool.meta == meta_data

        mcp_tool = tool.to_mcp_tool()
        assert "_meta" in mcp_tool
        assert mcp_tool["_meta"] == meta_data

    def test_to_mcp_tool_complex_nested_types(self):
        """Test MCP tool schema generation with complex nested types."""

        def create_complex_nested_action_schema() -> Schema:
            return Schema(
                name="ComplexNestedAction",
                fields=[
                    SchemaField(
                        name="simple_string",
                        type=SchemaFieldType.from_type(str),
                        description="Simple string field",
                        required=True,
                    ),
                    SchemaField(
                        name="optional_int",
                        type=SchemaFieldType.from_type(int),
                        description="Optional integer",
                        required=False,
                    ),
                    SchemaField(
                        name="string_array",
                        type=SchemaFieldType.from_type(List[str]),
                        description="Array of strings",
                        required=False,
                    ),
                    SchemaField(
                        name="int_array",
                        type=SchemaFieldType.from_type(List[int]),
                        description="Array of integers",
                        required=False,
                    ),
                    SchemaField(
                        name="nested_dict",
                        type=SchemaFieldType.from_type(Dict[str, str]),
                        description="Nested dictionary",
                        required=False,
                    ),
                    SchemaField(
                        name="optional_array",
                        type=SchemaFieldType.from_type(List[str]),
                        description="Optional array",
                        required=False,
                    ),
                ],
            )

        tool = Tool(
            name="complex_nested_tool",
            description="Tool with complex nested types",
            input_schema=create_complex_nested_action_schema(),
            output_schema=create_mock_observation_schema(),
        )

        mcp_tool = tool.to_mcp_tool()
        schema = mcp_tool["inputSchema"]
        props = schema["properties"]

        # Test simple string
        assert props["simple_string"]["type"] == "string"
        assert "simple_string" in schema["required"]

        # Test optional int
        optional_int_schema = props["optional_int"]
        assert "anyOf" not in optional_int_schema
        assert optional_int_schema["type"] == "integer"
        assert "optional_int" not in schema["required"]

        # Test string array
        string_array_schema = props["string_array"]
        assert string_array_schema["type"] == "array"
        assert string_array_schema["items"]["type"] == "string"

        # Test int array
        int_array_schema = props["int_array"]
        assert int_array_schema["type"] == "array"
        assert int_array_schema["items"]["type"] == "integer"

        # Test nested dict
        nested_dict_schema = props["nested_dict"]
        assert nested_dict_schema["type"] == "object"

        # Test optional array
        optional_array_schema = props["optional_array"]
        assert "anyOf" not in optional_array_schema
        assert optional_array_schema["type"] == "array"
        assert optional_array_schema["items"]["type"] == "string"
