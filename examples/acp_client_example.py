#!/usr/bin/env python3
"""
Example ACP client for testing OpenHands ACP server.

This demonstrates how to interact with the OpenHands ACP server using
the Agent Client Protocol over stdin/stdout.
"""

import json
import subprocess
import sys
from typing import Any


class ACPClient:
    """Simple ACP client for testing."""

    def __init__(self, server_command: list[str]):
        """Initialize the client with server command."""
        self.server_command = server_command
        self.process: subprocess.Popen[bytes] | None = None
        self.request_id = 0

    def start_server(self) -> None:
        """Start the ACP server process."""
        self.process = subprocess.Popen(
            self.server_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
        )
        print("🚀 ACP server started")

    def stop_server(self) -> None:
        """Stop the ACP server process."""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        print("🛑 Server stopped")

    def send_request(
        self, method: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and return the response."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            raise RuntimeError("Server not started")

        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id,
        }

        # Send request
        request_line = json.dumps(request) + "\n"
        self.process.stdin.write(request_line.encode())
        self.process.stdin.flush()

        # Read response
        response_line = self.process.stdout.readline().decode().strip()
        if not response_line:
            raise RuntimeError("No response from server")

        try:
            response = json.loads(response_line)
            if "error" in response:
                raise RuntimeError(f"Server error: {response['error']}")
            return response.get("result", {})
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {e}")

    def send_notification(
        self, method: str, params: dict[str, Any] | None = None
    ) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Server not started")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

        # Send notification
        notification_line = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_line.encode())
        self.process.stdin.flush()


def main() -> int:
    """Main function to demonstrate ACP client usage."""
    # Server command
    server_cmd = [
        sys.executable,
        "-m",
        "openhands.agent_server",
        "--mode",
        "acp",
        "--persistence-dir",
        "/tmp/acp_test",
    ]

    client = ACPClient(server_cmd)

    try:
        # Start server
        client.start_server()

        print("\n🔧 Step 1: Initialize protocol")
        init_result = client.send_request(
            "initialize",
            {
                "protocolVersion": "1.0.0",
                "clientCapabilities": {
                    "fs": {"readTextFile": True, "writeTextFile": False},
                    "terminal": False,
                },
            },
        )
        print(f"✅ Initialized: {init_result}")

        print("\n🔐 Step 2: Authenticate")
        auth_result = client.send_request("authenticate", {})
        print(f"✅ Authenticated: {auth_result}")

        print("\n📝 Step 3: Create new session")
        session_result = client.send_request(
            "session/new", {"workingDirectory": "/tmp"}
        )
        session_id = session_result["sessionId"]
        print(f"✅ Session created: {session_id}")

        print("\n💬 Step 4: Send prompt")
        prompt_result = client.send_request(
            "session/prompt",
            {
                "sessionId": session_id,
                "prompt": [{"type": "text", "text": "Hello! Can you help me?"}],
            },
        )
        print(f"✅ Prompt response: {prompt_result}")

        print("\n🎉 ACP client demo completed successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    finally:
        client.stop_server()

    return 0


if __name__ == "__main__":
    sys.exit(main())
