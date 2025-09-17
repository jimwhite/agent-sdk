"""Tests for SchemaInstance immutability in openhands.sdk.tool.schema."""

import pytest
from pydantic import ValidationError

from openhands.sdk.tool.schema import Schema, SchemaField, SchemaInstance


def create_test_schema() -> Schema:
    """Create a test schema for testing."""
    return Schema(
        name="test.schema",
        fields=[
            SchemaField.create(
                name="command",
                description="Command to execute",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="value",
                description="Value field",
                type=int,
                required=False,
                default=42,
            ),
        ],
    )


def test_schema_instance_is_frozen():
    """Test that SchemaInstance instances are frozen and cannot be modified."""
    schema = create_test_schema()
    instance = SchemaInstance(
        schema=schema,
        data={"command": "test_command", "value": 100}
    )

    # Test that we cannot modify the schema
    with pytest.raises(ValidationError, match="Instance is frozen"):
        instance.schema = create_test_schema()

    # Test that we cannot modify the data
    with pytest.raises(ValidationError, match="Instance is frozen"):
        instance.data = {"command": "modified"}


def test_schema_instance_model_copy_creates_new_instance():
    """Test that model_copy creates a new instance with updated fields."""
    schema = create_test_schema()
    original = SchemaInstance(
        schema=schema,
        data={"command": "original_command", "value": 10}
    )

    # Create a copy with updated data
    updated = original.model_copy(
        update={"data": {"command": "updated_command", "value": 20}}
    )

    # Verify original is unchanged
    assert original.data["command"] == "original_command"
    assert original.data["value"] == 10

    # Verify updated instance has new values
    assert updated.data["command"] == "updated_command"
    assert updated.data["value"] == 20

    # Verify they are different instances
    assert original is not updated
    assert original.schema is updated.schema  # Schema should be shared


def test_schema_instance_immutability_prevents_mutation_bugs():
    """Test a practical scenario where immutability prevents mutation bugs."""
    schema = create_test_schema()
    shared_instance = SchemaInstance(
        schema=schema,
        data={"command": "shared_cmd", "value": 42}
    )

    # Simulate two different contexts trying to modify the instance
    def context_a_processing(instance: SchemaInstance) -> SchemaInstance:
        # Context A wants to modify the data - this should fail
        with pytest.raises(ValidationError, match="Instance is frozen"):
            instance.data["command"] = "context_a_cmd"

        # Context A should use model_copy instead
        new_data = instance.data.copy()
        new_data["command"] = "context_a_cmd"
        return instance.model_copy(update={"data": new_data})

    def context_b_processing(instance: SchemaInstance) -> SchemaInstance:
        # Context B wants to change the value - this should fail
        with pytest.raises(ValidationError, match="Instance is frozen"):
            instance.data["value"] = 999

        # Context B should use model_copy instead
        new_data = instance.data.copy()
        new_data["value"] = 999
        return instance.model_copy(update={"data": new_data})

    # Process the instance in both contexts
    instance_a = context_a_processing(shared_instance)
    instance_b = context_b_processing(shared_instance)

    # Verify the original instance is unchanged
    assert shared_instance.data["command"] == "shared_cmd"
    assert shared_instance.data["value"] == 42

    # Verify each context got its own modified version
    assert instance_a.data["command"] == "context_a_cmd"
    assert instance_a.data["value"] == 42

    assert instance_b.data["command"] == "shared_cmd"
    assert instance_b.data["value"] == 999

    # Verify all instances are different
    assert shared_instance is not instance_a
    assert shared_instance is not instance_b
    assert instance_a is not instance_b


def test_schema_is_frozen():
    """Test that Schema instances are frozen and cannot be modified."""
    schema = create_test_schema()

    # Test that we cannot modify the name
    with pytest.raises(ValidationError, match="Instance is frozen"):
        schema.name = "modified.schema"

    # Test that we cannot modify the fields list
    with pytest.raises(ValidationError, match="Instance is frozen"):
        schema.fields = []


def test_schema_field_is_frozen():
    """Test that SchemaField instances are frozen and cannot be modified."""
    field = SchemaField.create(
        name="test_field",
        description="Test field",
        type=str,
        required=True,
    )

    # Test that we cannot modify any field
    with pytest.raises(ValidationError, match="Instance is frozen"):
        field.name = "modified_field"

    with pytest.raises(ValidationError, match="Instance is frozen"):
        field.description = "Modified description"

    with pytest.raises(ValidationError, match="Instance is frozen"):
        field.required = False