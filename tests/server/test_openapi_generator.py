"""Tests for OpenAPI generator utility."""

from openhands.server.utils.openapi_generator import (
    extract_conversation_methods,
    extract_conversation_state_properties,
    generate_endpoint_mapping,
    generate_openapi_spec,
)


def test_extract_conversation_methods():
    """Test extracting methods from Conversation class."""
    methods = extract_conversation_methods()

    # Should contain key methods
    assert "send_message" in methods
    assert "run" in methods
    assert "set_confirmation_mode" in methods
    assert "reject_pending_actions" in methods
    assert "pause" in methods
    assert "__init__" in methods

    # Check method info structure
    send_message_info = methods["send_message"]
    assert "parameters" in send_message_info
    assert "return_type" in send_message_info
    assert "docstring" in send_message_info
    assert "is_property" in send_message_info
    assert not send_message_info["is_property"]


def test_extract_conversation_state_properties():
    """Test extracting properties from ConversationState class."""
    properties = extract_conversation_state_properties()

    # Should contain key properties
    expected_properties = [
        "id",
        "events",
        "agent_finished",
        "confirmation_mode",
        "agent_waiting_for_confirmation",
        "agent_paused",
        "activated_knowledge_microagents",
    ]

    for prop in expected_properties:
        assert prop in properties
        assert "type" in properties[prop]
        assert "description" in properties[prop]


def test_generate_endpoint_mapping():
    """Test generating HTTP endpoint mapping."""
    endpoints = generate_endpoint_mapping()

    # Should contain key endpoints
    assert "/conversations" in endpoints
    assert "/conversations/{conversation_id}" in endpoints
    assert "/conversations/{conversation_id}/send_message" in endpoints
    assert "/conversations/{conversation_id}/run" in endpoints
    assert "/conversations/{conversation_id}/set_confirmation_mode" in endpoints
    assert "/conversations/{conversation_id}/reject_pending_actions" in endpoints
    assert "/conversations/{conversation_id}/pause" in endpoints
    assert "/conversations/{conversation_id}/events" in endpoints
    assert "/conversations/{conversation_id}/state" in endpoints

    # Check endpoint structure
    create_endpoint = endpoints["/conversations"]
    assert create_endpoint["method"] == "POST"
    assert create_endpoint["operation_id"] == "create_conversation"
    assert "summary" in create_endpoint
    assert "description" in create_endpoint


def test_generate_openapi_spec():
    """Test generating complete OpenAPI specification."""
    spec = generate_openapi_spec()

    # Check OpenAPI structure
    assert spec["openapi"] == "3.0.0"
    assert "info" in spec
    assert "servers" in spec
    assert "security" in spec
    assert "components" in spec
    assert "paths" in spec

    # Check info section
    assert spec["info"]["title"] == "OpenHands Agent SDK API"
    assert spec["info"]["version"] == "1.0.0"
    assert "description" in spec["info"]

    # Check security scheme
    assert "securitySchemes" in spec["components"]
    assert "BearerAuth" in spec["components"]["securitySchemes"]

    # Check paths
    assert len(spec["paths"]) > 0

    # Verify some key paths exist
    paths = spec["paths"]
    assert "/conversations/{conversation_id}/send_message" in paths
    assert "/conversations/{conversation_id}/run" in paths


def test_openapi_spec_validation():
    """Test that generated OpenAPI spec is valid."""
    spec = generate_openapi_spec()

    # Basic validation checks
    assert isinstance(spec, dict)
    assert spec.get("openapi") == "3.0.0"
    assert isinstance(spec.get("info"), dict)
    assert isinstance(spec.get("paths"), dict)
    assert isinstance(spec.get("components"), dict)

    # Check that all paths have valid operations
    for path, operations in spec["paths"].items():
        assert isinstance(operations, dict)
        for method, operation in operations.items():
            if isinstance(operation, dict):
                assert "operationId" in operation
                assert "summary" in operation
                assert "responses" in operation
