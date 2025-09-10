"""Automatic OpenAPI generation from Conversation class methods."""

import inspect
from typing import Any, Dict, get_type_hints


try:
    from openhands.sdk.conversation.conversation import Conversation
    from openhands.sdk.conversation.state import ConversationState
    from openhands.sdk.llm.llm import LLM
except ImportError:
    # Handle case where SDK is not installed
    print("Warning: OpenHands SDK not found. Using mock classes for testing.")
    Conversation = type("Conversation", (), {})
    ConversationState = type("ConversationState", (), {})
    LLM = type("LLM", (), {})


def extract_conversation_methods() -> Dict[str, Dict[str, Any]]:
    """Extract public methods from Conversation class for API generation.

    Returns:
        Dictionary mapping method names to their metadata including:
        - parameters: List of parameter info
        - return_type: Return type annotation
        - docstring: Method documentation
        - is_property: Whether it's a property
    """
    methods = {}

    # Check if we have the real Conversation class or a mock
    if not hasattr(Conversation, "__module__") or "openhands.sdk" not in getattr(
        Conversation, "__module__", ""
    ):
        # Return mock methods for testing
        return {
            "__init__": {
                "name": "__init__",
                "is_property": False,
                "docstring": (
                    "Initialize self.  See help(type(self)) for accurate signature."
                ),
                "parameters": [],
                "return_type": None,
            }
        }

    # Get all public methods and properties
    for name, method in inspect.getmembers(Conversation):
        # Skip private methods and special methods (except __init__)
        if name.startswith("_") and name != "__init__":
            continue

        # Skip non-callable attributes that aren't properties
        if not callable(method) and not isinstance(method, property):
            continue

        method_info = {
            "name": name,
            "is_property": isinstance(method, property),
            "docstring": inspect.getdoc(method) or "",
            "parameters": [],
            "return_type": None,
        }

        if isinstance(method, property):
            # Handle properties
            if method.fget:
                try:
                    sig = inspect.signature(method.fget)
                    type_hints = get_type_hints(method.fget)
                    method_info["return_type"] = type_hints.get("return", None)
                except (NameError, AttributeError) as e:
                    print(f"Warning: Could not get type hints for property {name}: {e}")
                    method_info["return_type"] = None
        else:
            # Handle regular methods
            try:
                sig = inspect.signature(method)
                try:
                    type_hints = get_type_hints(method)
                except (NameError, AttributeError) as e:
                    print(f"Warning: Could not get type hints for {name}: {e}")
                    type_hints = {}

                # Extract parameters (skip 'self')
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue

                    param_info = {
                        "name": param_name,
                        "type": type_hints.get(param_name, param.annotation),
                        "default": param.default
                        if param.default != inspect.Parameter.empty
                        else None,
                        "required": param.default == inspect.Parameter.empty,
                    }
                    method_info["parameters"].append(param_info)

                # Extract return type
                method_info["return_type"] = type_hints.get(
                    "return", sig.return_annotation
                )

            except (ValueError, TypeError) as e:
                # Some methods might not have proper signatures
                print(f"Warning: Could not extract signature for {name}: {e}")

        methods[name] = method_info

    return methods


def extract_conversation_state_properties() -> Dict[str, Dict[str, Any]]:
    """Extract properties from ConversationState class.

    Returns:
        Dictionary mapping property names to their metadata.
    """
    properties = {}

    # Get type hints for ConversationState
    type_hints = get_type_hints(ConversationState)

    for name, type_hint in type_hints.items():
        if name.startswith("_"):
            continue

        properties[name] = {
            "name": name,
            "type": type_hint,
            "description": f"ConversationState.{name} property",
        }

    return properties


def generate_endpoint_mapping() -> Dict[str, Dict[str, Any]]:
    """Generate HTTP endpoint mapping from Conversation methods.

    Returns:
        Dictionary mapping endpoint paths to HTTP method info.
    """
    conversation_methods = extract_conversation_methods()

    endpoints = {}

    # Map conversation methods to endpoints
    for method_name, method_info in conversation_methods.items():
        if method_name == "__init__":
            # Constructor maps to POST /conversations
            endpoints["/conversations"] = {
                "method": "POST",
                "operation_id": "create_conversation",
                "summary": "Create new conversation",
                "description": method_info["docstring"],
                "parameters": method_info["parameters"],
                "response_model": "ConversationResponse",
            }
        elif method_name == "id" and method_info["is_property"]:
            # ID property maps to GET /conversations/{id}
            endpoints["/conversations/{conversation_id}"] = {
                "method": "GET",
                "operation_id": "get_conversation",
                "summary": "Get conversation info",
                "description": method_info["docstring"],
                "parameters": [],
                "response_model": "ConversationResponse",
            }
        elif not method_info["is_property"]:
            # Regular methods map to POST endpoints
            endpoint_path = f"/conversations/{{conversation_id}}/{method_name}"
            endpoints[endpoint_path] = {
                "method": "POST",
                "operation_id": method_name,
                "summary": f"Call {method_name} method",
                "description": method_info["docstring"],
                "parameters": method_info["parameters"],
                "response_model": "StatusResponse",
            }

    # Add state access endpoints
    endpoints["/conversations/{conversation_id}/events"] = {
        "method": "GET",
        "operation_id": "get_events",
        "summary": "Get conversation events",
        "description": "Get all events from conversation state",
        "parameters": [],
        "response_model": "List[Dict[str, Any]]",
    }

    endpoints["/conversations/{conversation_id}/state"] = {
        "method": "GET",
        "operation_id": "get_state",
        "summary": "Get conversation state",
        "description": "Get full conversation state",
        "parameters": [],
        "response_model": "ConversationStateResponse",
    }

    # Add management endpoints
    endpoints["/conversations"] = {
        **endpoints.get("/conversations", {}),
        "get": {
            "method": "GET",
            "operation_id": "list_conversations",
            "summary": "List all conversations",
            "description": "Get list of all active conversations",
            "parameters": [],
            "response_model": "List[ConversationResponse]",
        },
    }

    endpoints["/conversations/{conversation_id}"] = {
        **endpoints.get("/conversations/{conversation_id}", {}),
        "delete": {
            "method": "DELETE",
            "operation_id": "delete_conversation",
            "summary": "Delete conversation",
            "description": "Delete conversation and clean up resources",
            "parameters": [],
            "response_model": "StatusResponse",
        },
    }

    return endpoints


def generate_openapi_spec() -> Dict[str, Any]:
    """Generate complete OpenAPI specification.

    Returns:
        OpenAPI 3.0 specification dictionary.
    """
    endpoints = generate_endpoint_mapping()

    # Base OpenAPI structure
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "OpenHands Agent SDK API",
            "description": (
                "REST API with 1-1 mapping to Conversation class methods. "
                "Automatically generated from the SDK class definitions."
            ),
            "version": "1.0.0",
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Development server"}
        ],
        "security": [{"BearerAuth": []}],
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": "Master key authentication",
                }
            },
            "schemas": {
                # Will be populated by FastAPI automatically from Pydantic models
            },
        },
        "paths": {},
    }

    # Convert endpoints to OpenAPI paths
    for path, endpoint_info in endpoints.items():
        if path not in spec["paths"]:
            spec["paths"][path] = {}

        # Handle multiple methods for same path
        if "get" in endpoint_info:
            spec["paths"][path]["get"] = _create_operation(endpoint_info["get"])
        if "method" in endpoint_info:
            method = endpoint_info["method"].lower()
            spec["paths"][path][method] = _create_operation(endpoint_info)

    return spec


def _create_operation(endpoint_info: Dict[str, Any]) -> Dict[str, Any]:
    """Create OpenAPI operation object from endpoint info."""
    operation = {
        "operationId": endpoint_info["operation_id"],
        "summary": endpoint_info["summary"],
        "description": endpoint_info["description"],
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}  # Will be refined by FastAPI
                    }
                },
            },
            "401": {"description": "Unauthorized - Invalid master key"},
            "404": {"description": "Conversation not found"},
            "500": {"description": "Internal server error"},
        },
    }

    # Add parameters if any
    if endpoint_info["parameters"]:
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "object"}  # Will be refined by FastAPI
                }
            },
        }

    return operation


if __name__ == "__main__":
    # Generate and print the OpenAPI spec
    import json

    print("=== Conversation Methods ===")
    methods = extract_conversation_methods()
    for name, info in methods.items():
        print(f"{name}: {info['docstring'][:50]}...")

    print("\n=== State Properties ===")
    properties = extract_conversation_state_properties()
    for name, info in properties.items():
        print(f"{name}: {info['type']}")

    print("\n=== Generated Endpoints ===")
    endpoints = generate_endpoint_mapping()
    for path, info in endpoints.items():
        method = info.get("method", "GET")
        print(f"{method} {path}: {info.get('summary', '')}")

    print("\n=== OpenAPI Spec ===")
    spec = generate_openapi_spec()
    print(json.dumps(spec, indent=2))
