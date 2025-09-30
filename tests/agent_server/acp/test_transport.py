"""Tests for JSON-RPC transport."""

import json
from unittest.mock import Mock, patch

from openhands.agent_server.acp.transport import JSONRPCTransport


def test_register_handler():
    """Test handler registration."""
    transport = JSONRPCTransport()
    handler = Mock(return_value={"result": "test"})

    transport.register_handler("test_method", handler)

    assert "test_method" in transport.handlers
    assert transport.handlers["test_method"] == handler


def test_send_notification():
    """Test sending notifications."""
    transport = JSONRPCTransport()

    with patch("builtins.print") as mock_print:
        transport.send_notification("test_method", {"param": "value"})

        # Verify the printed JSON
        mock_print.assert_called_once()
        printed_json = mock_print.call_args[0][0]
        message = json.loads(printed_json)

        assert message["jsonrpc"] == "2.0"
        assert message["method"] == "test_method"
        assert message["params"] == {"param": "value"}
        assert "id" not in message


def test_send_response():
    """Test sending responses."""
    transport = JSONRPCTransport()

    with patch("builtins.print") as mock_print:
        transport.send_response({"result": "test"}, "test-id")

        # Verify the printed JSON
        mock_print.assert_called_once()
        printed_json = mock_print.call_args[0][0]
        message = json.loads(printed_json)

        assert message["jsonrpc"] == "2.0"
        assert message["result"] == {"result": "test"}
        assert message["id"] == "test-id"


def test_send_error_response():
    """Test sending error responses."""
    transport = JSONRPCTransport()

    with patch("builtins.print") as mock_print:
        transport.send_error_response(-32601, "Method not found", "test-id")

        # Verify the printed JSON
        mock_print.assert_called_once()
        printed_json = mock_print.call_args[0][0]
        message = json.loads(printed_json)

        assert message["jsonrpc"] == "2.0"
        assert message["error"]["code"] == -32601
        assert message["error"]["message"] == "Method not found"
        assert message["id"] == "test-id"


def test_handle_request_message():
    """Test handling request messages."""
    transport = JSONRPCTransport()
    handler = Mock(return_value={"result": "test"})
    transport.register_handler("test_method", handler)

    message = {
        "jsonrpc": "2.0",
        "method": "test_method",
        "params": {"param": "value"},
        "id": "test-id",
    }

    with patch.object(transport, "send_response") as mock_send_response:
        transport.handle_message(message)

        handler.assert_called_once_with({"param": "value"})
        mock_send_response.assert_called_once_with({"result": "test"}, "test-id")


def test_handle_notification_message():
    """Test handling notification messages."""
    transport = JSONRPCTransport()
    handler = Mock()
    transport.register_handler("test_method", handler)

    message = {
        "jsonrpc": "2.0",
        "method": "test_method",
        "params": {"param": "value"},
    }

    transport.handle_message(message)

    handler.assert_called_once_with({"param": "value"})


def test_handle_unknown_method():
    """Test handling unknown methods."""
    transport = JSONRPCTransport()

    message = {
        "jsonrpc": "2.0",
        "method": "unknown_method",
        "params": {"param": "value"},
        "id": "test-id",
    }

    with patch.object(transport, "send_error_response") as mock_send_error:
        transport.handle_message(message)

        mock_send_error.assert_called_once_with(
            -32601, "Method not found: unknown_method", "test-id"
        )


def test_handle_response_message():
    """Test handling response messages (should be ignored)."""
    transport = JSONRPCTransport()

    message = {
        "jsonrpc": "2.0",
        "result": {"data": "test"},
        "id": "test-id",
    }

    # Should not raise any exceptions
    transport.handle_message(message)


def test_handle_error_response_message():
    """Test handling error response messages (should be ignored)."""
    transport = JSONRPCTransport()

    message = {
        "jsonrpc": "2.0",
        "error": {"code": -32601, "message": "Method not found"},
        "id": "test-id",
    }

    # Should not raise any exceptions
    transport.handle_message(message)
