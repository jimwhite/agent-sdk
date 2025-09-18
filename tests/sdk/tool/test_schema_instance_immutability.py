"""Tests for SchemaInstance immutability in openhands.sdk.tool.schema."""

import pytest
from pydantic import ValidationError

from openhands.sdk.tool.schema import Schema, SchemaField, SchemaInstance
from openhands.sdk.tool.schema.types import SchemaFieldType


def create_test_schema() -> Schema:
    """Create a schema suitable for immutability tests."""
    return Schema(
        name="tests.schemaInstance.action",
        fields=[
            SchemaField(
                name="command",
                description="Command to execute",
                type=SchemaFieldType.from_type(str),
                required=True,
            ),
            SchemaField(
                name="value",
                description="Optional value",
                type=SchemaFieldType.from_type(int),
                required=False,
                default=42,
            ),
        ],
    )


def create_schema_instance(
    command: str = "test_command", value: int = 100
) -> SchemaInstance:
    """Helper to create an immutable SchemaInstance."""
    schema = create_test_schema()
    return SchemaInstance(
        name="testAction",
        definition=schema,
        data={"command": command, "value": value},
    )


def test_schema_instance_is_frozen() -> None:
    """SchemaInstance should forbid reassignment of top-level fields."""
    instance = create_schema_instance()

    with pytest.raises(ValidationError, match="Instance is frozen"):
        instance.name = "otherAction"  # type: ignore[assignment]

    with pytest.raises(ValidationError, match="Instance is frozen"):
        instance.definition = create_test_schema()  # type: ignore[assignment]

    with pytest.raises(ValidationError, match="Instance is frozen"):
        instance.data = {"command": "modified"}  # type: ignore[assignment]


def test_schema_instance_model_copy_creates_new_instance() -> None:
    """model_copy should return a new instance with updated data."""
    original = create_schema_instance(command="original", value=10)

    updated = original.model_copy(update={"data": {"command": "updated", "value": 20}})

    assert updated is not original
    assert original.data == {"command": "original", "value": 10}
    assert updated.data == {"command": "updated", "value": 20}
    assert original.definition is updated.definition


def test_schema_instance_copy_helpers_prevent_mutation_bugs() -> None:
    """Use model_copy to create independent variants without mutating the original."""
    shared = create_schema_instance(command="shared", value=1)

    # Create variants without mutating the shared instance
    variant_a = shared.model_copy(
        update={"data": {**shared.data, "command": "variant_a"}}
    )
    variant_b = shared.model_copy(update={"data": {**shared.data, "value": 999}})

    assert shared.data == {"command": "shared", "value": 1}
    assert variant_a.data == {"command": "variant_a", "value": 1}
    assert variant_b.data == {"command": "shared", "value": 999}
    assert variant_a is not shared and variant_b is not shared


def test_schema_is_frozen() -> None:
    """Schema should also be immutable after creation."""
    schema = create_test_schema()

    with pytest.raises(ValidationError, match="Instance is frozen"):
        schema.name = "tests.other.action"  # type: ignore[assignment]

    with pytest.raises(ValidationError, match="Instance is frozen"):
        schema.fields = []  # type: ignore[assignment]


def test_schema_field_is_frozen() -> None:
    """SchemaField instances should be immutable."""
    field = SchemaField(
        name="test_field",
        description="Test field",
        type=SchemaFieldType.from_type(str),
        required=True,
    )

    with pytest.raises(ValidationError, match="Instance is frozen"):
        field.name = "renamed"  # type: ignore[assignment]

    with pytest.raises(ValidationError, match="Instance is frozen"):
        field.description = "Modified"  # type: ignore[assignment]

    with pytest.raises(ValidationError, match="Instance is frozen"):
        field.required = False  # type: ignore[assignment]
