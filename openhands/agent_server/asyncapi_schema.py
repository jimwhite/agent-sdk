"""
AsyncAPI schema generation for OpenHands Agent Server WebSocket endpoints.

This module provides functionality to generate AsyncAPI documentation for the
WebSocket endpoints defined in sockets.py, complementing the existing OpenAPI
documentation for REST endpoints.
"""

from typing import Any

from openhands.agent_server.models import BashEventBase
from openhands.sdk import Event, Message


def get_message_schema() -> dict[str, Any]:
    """Generate JSON schema for Message model."""
    return Message.model_json_schema()


def get_event_schema() -> dict[str, Any]:
    """Generate JSON schema for Event model."""
    return Event.model_json_schema()


def get_bash_event_schema() -> dict[str, Any]:
    """Generate JSON schema for BashEventBase model."""
    return BashEventBase.model_json_schema()


def generate_asyncapi_schema(
    server_url: str = "ws://localhost:8000",
    title: str = "OpenHands Agent Server WebSocket API",
    version: str = "1.0.0",
) -> dict[str, Any]:
    """
    Generate AsyncAPI 3.0.0 schema for WebSocket endpoints.

    Args:
        server_url: Base WebSocket server URL
        title: API title
        version: API version

    Returns:
        Complete AsyncAPI schema as dictionary
    """
    # Get schemas for message types
    message_schema = get_message_schema()
    event_schema = get_event_schema()
    bash_event_schema = get_bash_event_schema()

    asyncapi_schema = {
        "asyncapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": (
                "WebSocket API for OpenHands Agent Server providing real-time "
                "communication for conversation events and bash command execution."
            ),
        },
        "servers": {
            "production": {
                "host": server_url.replace("ws://", "").replace("wss://", ""),
                "protocol": "ws" if server_url.startswith("ws://") else "wss",
                "description": "OpenHands Agent Server WebSocket endpoint",
            }
        },
        "channels": {
            "conversationEvents": {
                "address": "/sockets/events/{conversationId}",
                "title": "Conversation Events",
                "summary": "Real-time conversation events and message exchange",
                "description": (
                    "WebSocket channel for bidirectional communication between "
                    "clients and the OpenHands agent. Clients can send messages "
                    "and receive real-time events from the conversation."
                ),
                "parameters": {
                    "conversationId": {
                        "description": "UUID of the conversation to connect to",
                        "schema": {"type": "string", "format": "uuid"},
                    }
                },
                "messages": {
                    "messageFromClient": {"$ref": "#/components/messages/Message"},
                    "eventToClient": {"$ref": "#/components/messages/Event"},
                },
            },
            "bashEvents": {
                "address": "/sockets/bash-events",
                "title": "Bash Events",
                "summary": "Real-time bash command execution events",
                "description": (
                    "WebSocket channel for receiving real-time events from bash "
                    "command execution. Primarily server-to-client communication "
                    "with occasional keep-alive messages from clients."
                ),
                "messages": {
                    "keepAlive": {"$ref": "#/components/messages/KeepAlive"},
                    "bashEvent": {"$ref": "#/components/messages/BashEvent"},
                },
            },
        },
        "operations": {
            "sendMessage": {
                "action": "send",
                "channel": {"$ref": "#/channels/conversationEvents"},
                "title": "Send Message",
                "summary": "Send a message to the conversation",
                "description": (
                    "Send a message from the client to the OpenHands agent. "
                    "The message will be processed and may trigger various events."
                ),
                "messages": [
                    {"$ref": "#/channels/conversationEvents/messages/messageFromClient"}
                ],
            },
            "receiveEvent": {
                "action": "receive",
                "channel": {"$ref": "#/channels/conversationEvents"},
                "title": "Receive Event",
                "summary": "Receive events from the conversation",
                "description": (
                    "Receive real-time events generated during the conversation, "
                    "including agent responses, tool executions, and status updates."
                ),
                "messages": [
                    {"$ref": "#/channels/conversationEvents/messages/eventToClient"}
                ],
            },
            "sendKeepAlive": {
                "action": "send",
                "channel": {"$ref": "#/channels/bashEvents"},
                "title": "Send Keep Alive",
                "summary": "Send keep-alive message",
                "description": (
                    "Send a keep-alive message to maintain the WebSocket connection "
                    "for bash events. Content is typically ignored."
                ),
                "messages": [{"$ref": "#/channels/bashEvents/messages/keepAlive"}],
            },
            "receiveBashEvent": {
                "action": "receive",
                "channel": {"$ref": "#/channels/bashEvents"},
                "title": "Receive Bash Event",
                "summary": "Receive bash execution events",
                "description": (
                    "Receive real-time events from bash command execution, "
                    "including command output, completion status, and errors."
                ),
                "messages": [{"$ref": "#/channels/bashEvents/messages/bashEvent"}],
            },
        },
        "components": {
            "messages": {
                "Message": {
                    "name": "Message",
                    "title": "Message",
                    "summary": "Message sent from client to agent",
                    "description": (
                        "A message object containing user input or system instructions "
                        "to be processed by the OpenHands agent."
                    ),
                    "contentType": "application/json",
                    "payload": {"$ref": "#/components/schemas/Message"},
                },
                "Event": {
                    "name": "Event",
                    "title": "Event",
                    "summary": "Event sent from agent to client",
                    "description": (
                        "An event object representing something that happened during "
                        "the conversation, such as agent responses or tool executions."
                    ),
                    "contentType": "application/json",
                    "payload": {"$ref": "#/components/schemas/Event"},
                },
                "BashEvent": {
                    "name": "BashEvent",
                    "title": "Bash Event",
                    "summary": "Bash command execution event",
                    "description": (
                        "An event related to bash command execution, including "
                        "command input, output, and completion status."
                    ),
                    "contentType": "application/json",
                    "payload": {"$ref": "#/components/schemas/BashEvent"},
                },
                "KeepAlive": {
                    "name": "KeepAlive",
                    "title": "Keep Alive",
                    "summary": "Keep-alive message",
                    "description": (
                        "A simple text message used to keep the WebSocket connection "
                        "alive. Content is typically ignored by the server."
                    ),
                    "contentType": "text/plain",
                    "payload": {"type": "string"},
                },
            },
            "schemas": {
                "Message": message_schema,
                "Event": event_schema,
                "BashEvent": bash_event_schema,
            },
            "securitySchemes": {
                "sessionApiKey": {
                    "type": "httpApiKey",
                    "name": "session_api_key",
                    "in": "query",
                    "description": (
                        "Session API key for authentication. Required when the server "
                        "is configured with session API keys."
                    ),
                }
            },
        },
    }

    return asyncapi_schema


def generate_asyncapi_json(
    server_url: str = "ws://localhost:8000",
    title: str = "OpenHands Agent Server WebSocket API",
    version: str = "1.0.0",
) -> str:
    """
    Generate AsyncAPI schema as JSON string.

    Args:
        server_url: Base WebSocket server URL
        title: API title
        version: API version

    Returns:
        AsyncAPI schema as formatted JSON string
    """
    import json

    schema = generate_asyncapi_schema(server_url, title, version)
    return json.dumps(schema, indent=2)


def generate_asyncapi_yaml(
    server_url: str = "ws://localhost:8000",
    title: str = "OpenHands Agent Server WebSocket API",
    version: str = "1.0.0",
) -> str:
    """
    Generate AsyncAPI schema as YAML string.

    Args:
        server_url: Base WebSocket server URL
        title: API title
        version: API version

    Returns:
        AsyncAPI schema as formatted YAML string
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required for YAML output. Install with: pip install pyyaml"
        )

    schema = generate_asyncapi_schema(server_url, title, version)
    return yaml.dump(schema, default_flow_style=False, sort_keys=False)
