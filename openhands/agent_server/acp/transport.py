"""JSON-RPC 2.0 transport layer for Agent Client Protocol."""

import json
import sys
from collections.abc import Callable
from typing import Any

from .models import (
    JSONRPCError,
    JSONRPCErrorResponse,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
)


class JSONRPCTransport:
    """JSON-RPC 2.0 transport over stdin/stdout using NDJSON format."""

    def __init__(self) -> None:
        """Initialize the transport."""
        self.handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        self.running = False

    def register_handler(
        self, method: str, handler: Callable[[dict[str, Any]], dict[str, Any]]
    ) -> None:
        """Register a method handler."""
        self.handlers[method] = handler

    def send_notification(
        self, method: str, params: dict[str, Any] | None = None
    ) -> None:
        """Send a JSON-RPC notification."""
        notification = JSONRPCNotification(method=method, params=params)
        self._send_message(notification.model_dump())

    def send_response(
        self, result: dict[str, Any], request_id: int | str | None
    ) -> None:
        """Send a JSON-RPC response."""
        response = JSONRPCResponse(result=result, id=request_id)
        self._send_message(response.model_dump())

    def send_error_response(
        self,
        code: int,
        message: str,
        request_id: int | str | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Send a JSON-RPC error response."""
        error = JSONRPCError(code=code, message=message, data=data)
        error_response = JSONRPCErrorResponse(error=error, id=request_id)
        self._send_message(error_response.model_dump())

    def _send_message(self, message: dict[str, Any]) -> None:
        """Send a message to stdout."""
        json_str = json.dumps(message)
        print(json_str, flush=True)

    def handle_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming JSON-RPC message."""
        if "method" in message:
            if "id" in message:
                # Request
                self._handle_request(message)
            else:
                # Notification
                self._handle_notification(message)
        elif "result" in message or "error" in message:
            # Response (we don't handle responses in server mode)
            pass

    def _handle_request(self, message: dict[str, Any]) -> None:
        """Handle a JSON-RPC request."""
        try:
            request = JSONRPCRequest.model_validate(message)
            method = request.method
            params = request.params or {}

            if method in self.handlers:
                try:
                    result = self.handlers[method](params)
                    self.send_response(result, request.id)
                except Exception as e:
                    self.send_error_response(-32603, f"Internal error: {e}", request.id)
            else:
                self.send_error_response(
                    -32601, f"Method not found: {method}", request.id
                )
        except Exception as e:
            self.send_error_response(-32700, f"Parse error: {e}", None)

    def _handle_notification(self, message: dict[str, Any]) -> None:
        """Handle a JSON-RPC notification."""
        try:
            notification = JSONRPCNotification.model_validate(message)
            method = notification.method
            params = notification.params or {}

            if method in self.handlers:
                try:
                    self.handlers[method](params)
                except Exception:
                    # Notifications don't send error responses
                    pass
        except Exception:
            # Notifications don't send error responses
            pass

    def run(self) -> None:
        """Run the transport, reading from stdin and processing messages."""
        self.running = True
        try:
            for line in sys.stdin:
                if not self.running:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                    self.handle_message(message)
                except json.JSONDecodeError:
                    self.send_error_response(-32700, "Parse error", None)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False

    def stop(self) -> None:
        """Stop the transport."""
        self.running = False
