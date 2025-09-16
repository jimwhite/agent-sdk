"""Tests for the new schema registry system."""

from pydantic import BaseModel, Field

from openhands.sdk.llm import TextContent
from openhands.sdk.tool.schema import ActionBase, ObservationBase
from openhands.sdk.tool.schema_registry import (
    SchemaRegistry,
    action_registry,
    kind_of,
    observation_registry,
    register_action_schema,
    register_observation_schema,
    validate_action,
    validate_observation,
)


class SampleAction(ActionBase):
    """Test action for registry testing."""

    message: str = Field(description="Test message")


class SampleObservation(ObservationBase):
    """Test observation for registry testing."""

    result: str = Field(description="Test result")

    @property
    def agent_observation(self):
        return [TextContent(text=self.result)]


def test_kind_of():
    """Test kind_of function generates correct kind strings."""
    assert kind_of(SampleAction) == "tests.sdk.tool.test_schema_registry.SampleAction"
    assert (
        kind_of(SampleObservation)
        == "tests.sdk.tool.test_schema_registry.SampleObservation"
    )


def test_schema_registry_basic():
    """Test basic schema registry functionality."""
    registry = SchemaRegistry()

    # Register a schema
    registry.register_schema(SampleAction)

    # Retrieve it
    retrieved = registry.get_schema(kind_of(SampleAction))
    assert retrieved is SampleAction


def test_schema_registry_auto_registration():
    """Test that schemas are auto-registered when defined."""
    # SampleAction and SampleObservation should be auto-registered
    assert action_registry.get_schema(kind_of(SampleAction)) is SampleAction
    assert (
        observation_registry.get_schema(kind_of(SampleObservation)) is SampleObservation
    )


def test_validate_action():
    """Test action validation through registry."""
    # Test with instance
    action = SampleAction(message="hello")
    result = validate_action(action.model_dump())
    assert isinstance(result, SampleAction)
    assert result.message == "hello"

    # Test with dict containing kind
    data = {"kind": kind_of(SampleAction), "message": "world"}
    result = validate_action(data)
    assert isinstance(result, SampleAction)
    assert result.message == "world"


def test_validate_observation():
    """Test observation validation through registry."""
    # Test with instance
    obs = SampleObservation(result="success")
    result = validate_observation(obs.model_dump())
    assert isinstance(result, SampleObservation)
    assert result.result == "success"

    # Test with dict containing kind
    data = {"kind": kind_of(SampleObservation), "result": "done"}
    result = validate_observation(data)
    assert isinstance(result, SampleObservation)
    assert result.result == "done"


def test_schema_registry_fallback():
    """Test fallback behavior when kind is not found."""
    # Create data with unknown kind but no extra fields (ActionBase has extra="forbid")
    data = {"kind": "unknown.kind"}

    # Should still validate but return an ActionBase instance
    result = validate_action(data)
    assert isinstance(result, ActionBase)


def test_schema_registry_spec_reconstruction():
    """Test reconstruction from spec when kind is missing."""
    # Create a spec manually
    spec = {
        "title": "TestSpec",
        "fields": {"message": {"type": "str", "required": True}},
    }

    registry = SchemaRegistry()
    data = {"message": "test"}
    result = registry.create_from_spec(spec, data)

    assert isinstance(result, BaseModel)
    assert hasattr(result, "message")
    assert getattr(result, "message") == "test"


def test_manual_registration():
    """Test manual registration functions."""

    class ManualAction(ActionBase):
        value: int = Field(description="Test value")

    class ManualObservation(ObservationBase):
        output: str = Field(description="Test output")

        @property
        def agent_observation(self):
            return [TextContent(text=self.output)]

    # These should be auto-registered, but let's test manual registration too
    register_action_schema(ManualAction)
    register_observation_schema(ManualObservation)

    # Verify they're registered
    assert action_registry.get_schema(kind_of(ManualAction)) is ManualAction
    assert (
        observation_registry.get_schema(kind_of(ManualObservation)) is ManualObservation
    )


def test_schema_with_kind_field():
    """Test that schemas automatically get kind field set."""
    action = SampleAction(message="test")
    assert action.kind == kind_of(SampleAction)

    obs = SampleObservation(result="test")
    assert obs.kind == kind_of(SampleObservation)


def test_schema_serialization_includes_kind():
    """Test that serialized schemas include the kind field."""
    action = SampleAction(message="test")
    data = action.model_dump()
    assert "kind" in data
    assert data["kind"] == kind_of(SampleAction)

    obs = SampleObservation(result="test")
    data = obs.model_dump()
    assert "kind" in data
    assert data["kind"] == kind_of(SampleObservation)


def test_registry_import_resolution():
    """Test that registry can resolve kinds via import."""
    # This should work for our test classes
    kind = kind_of(SampleAction)
    resolved = action_registry._resolve_kind_via_import(kind)
    assert resolved is SampleAction

    kind = kind_of(SampleObservation)
    resolved = observation_registry._resolve_kind_via_import(kind)
    assert resolved is SampleObservation
