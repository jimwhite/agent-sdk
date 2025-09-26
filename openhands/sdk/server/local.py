from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from io import BytesIO
from pathlib import Path

import httpx

from openhands.sdk.logger import get_logger

from .base import BaseAgentServer, BashExecutionResult
from .port_utils import find_available_tcp_port


logger = get_logger(__name__)


def _stream_output(stream, prefix, target_stream):
    """Stream output from subprocess to target stream with prefix."""
    try:
        for line in iter(stream.readline, ""):
            if line:
                target_stream.write(f"[{prefix}] {line}")
                target_stream.flush()
    except Exception as e:
        print(f"Error streaming {prefix}: {e}", file=sys.stderr)
    finally:
        stream.close()


class LocalAgentServer(BaseAgentServer):
    """Run the Agent Server as a local subprocess for development.

    This implementation starts the OpenHands agent server as a subprocess
    on the local machine. It's useful for development and testing scenarios
    where you want to run the agent server locally without containerization.

    Example:
        with LocalAgentServer(port=8001) as server:
            # use server.base_url as the host for RemoteConversation
            conversation = Conversation(agent=agent, host=server.base_url)
            ...

    Args:
        port: Port to run the server on (default: auto-assigned)
        host: Host to bind to (default: "127.0.0.1")
        log_json: Whether to use JSON logging (default: True)
        extra_env: Additional environment variables for the server process
    """

    def __init__(
        self,
        port: int | None = None,
        host: str = "127.0.0.1",
        log_json: bool = True,
        extra_env: dict[str, str] | None = None,
    ):
        self.port = port or find_available_tcp_port()
        self.host = host
        self.log_json = log_json
        self.extra_env = extra_env or {}
        self.process = None
        self._base_url = f"http://{host}:{self.port}"
        self.stdout_thread = None
        self.stderr_thread = None

    def __enter__(self):
        """Start the API server subprocess."""
        logger.info(f"Starting OpenHands API server on {self.base_url}...")

        # Prepare environment
        env = {"LOG_JSON": str(self.log_json).lower(), **os.environ}
        env.update(self.extra_env)

        # Start the server process
        self.process = subprocess.Popen(
            [
                "python",
                "-m",
                "openhands.agent_server",
                "--port",
                str(self.port),
                "--host",
                self.host,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Start threads to stream stdout and stderr
        self.stdout_thread = threading.Thread(
            target=_stream_output,
            args=(self.process.stdout, "SERVER", sys.stdout),
            daemon=True,
        )
        self.stderr_thread = threading.Thread(
            target=_stream_output,
            args=(self.process.stderr, "SERVER", sys.stderr),
            daemon=True,
        )

        self.stdout_thread.start()
        self.stderr_thread.start()

        # Wait for server to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = httpx.get(f"{self.base_url}/health", timeout=1.0)
                if response.status_code == 200:
                    logger.info(f"API server is ready at {self.base_url}")
                    return self
            except Exception:
                pass

            if self.process.poll() is not None:
                # Process has terminated
                raise RuntimeError(
                    "Server process terminated unexpectedly. "
                    "Check the server logs above for details."
                )

            time.sleep(1)

        raise RuntimeError(f"Server failed to start after {max_retries} seconds")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the API server subprocess."""
        if self.process:
            logger.info("Stopping API server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Force killing API server...")
                self.process.kill()
                self.process.wait()

            # Wait for streaming threads to finish (they're daemon threads,
            # so they'll stop automatically)
            # But give them a moment to flush any remaining output
            time.sleep(0.5)
            logger.info("API server stopped.")

    def execute_bash(
        self,
        command: str,
        cwd: str | None = None,
        timeout: int = 30,
    ) -> BashExecutionResult:
        """Execute a bash command on the local system.

        Args:
            command: The bash command to execute
            timeout: Maximum time to wait for command completion (seconds)
            cwd: Working directory for command execution

        Returns:
            BashExecutionResult with command output and exit code

        Raises:
            RuntimeError: If the server is not running or request fails
        """
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Local agent server is not running")

        try:
            response = httpx.post(
                f"{self._base_url}/execute_bash",
                json={
                    "command": command,
                    "timeout": timeout,
                    "working_dir": cwd,
                },
                timeout=timeout + 10,  # Add buffer for HTTP overhead
            )
            response.raise_for_status()
            data = response.json()
            return BashExecutionResult(
                command_id=data.get("command_id", "local"),
                command=command,
                exit_code=data["exit_code"],
                output=data.get("stdout", "") + data.get("stderr", ""),
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to execute bash command: {e}") from e

    def upload_file(self, local_path: str | Path, remote_path: str) -> bool:
        """Upload a file from local filesystem to the server.

        Args:
            local_path: Path to the local file to upload
            remote_path: Destination path on the server

        Returns:
            True if upload was successful, False otherwise

        Raises:
            RuntimeError: If the server is not running or request fails
        """
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Local agent server is not running")

        local_file = Path(local_path)
        if not local_file.exists():
            logger.error(f"Local file does not exist: {local_path}")
            return False

        try:
            with open(local_file, "rb") as f:
                files = {"file": (remote_path, f, "application/octet-stream")}
                response = httpx.post(
                    f"{self._base_url}/upload_file",
                    files=files,
                    data={"path": remote_path},
                    timeout=30,
                )
                response.raise_for_status()
                return response.json().get("success", False)
        except httpx.HTTPError as e:
            logger.error(f"Failed to upload file: {e}")
            return False

    def upload_file_content(self, content: str | bytes, remote_path: str) -> bool:
        """Upload content directly as a file to the server.

        Args:
            content: Content to upload (string or bytes)
            remote_path: Destination path on the server

        Returns:
            True if upload was successful, False otherwise

        Raises:
            RuntimeError: If the server is not running or request fails
        """
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Local agent server is not running")

        try:
            if isinstance(content, str):
                content = content.encode("utf-8")

            files = {
                "file": (remote_path, BytesIO(content), "application/octet-stream")
            }
            response = httpx.post(
                f"{self._base_url}/upload_file",
                files=files,
                data={"path": remote_path},
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("success", False)
        except httpx.HTTPError as e:
            logger.error(f"Failed to upload file content: {e}")
            return False

    def download_file(
        self, remote_path: str, local_path: str | Path | None = None
    ) -> bytes | None:
        """Download a file from the server.

        Args:
            remote_path: Path to the file on the server
            local_path: Optional local path to save the file

        Returns:
            File content as bytes if local_path is None, otherwise None

        Raises:
            RuntimeError: If the server is not running or file doesn't exist
        """
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Local agent server is not running")

        try:
            response = httpx.get(
                f"{self._base_url}/download_file",
                params={"path": remote_path},
                timeout=30,
            )
            response.raise_for_status()

            content = response.content
            if local_path:
                Path(local_path).write_bytes(content)
                return None
            return content
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise RuntimeError(f"File not found: {remote_path}") from e
            raise RuntimeError(f"Failed to download file: {e}") from e
        except httpx.HTTPError as e:
            raise RuntimeError(f"Failed to download file: {e}") from e

    def health(self) -> dict[str, str]:
        """Check the health status of the server.

        Returns:
            Dictionary with health status information

        Raises:
            RuntimeError: If the server is not running or health check fails
        """
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("Local agent server is not running")

        try:
            response = httpx.get(f"{self._base_url}/health", timeout=10)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            raise RuntimeError(f"Health check failed: {e}") from e
