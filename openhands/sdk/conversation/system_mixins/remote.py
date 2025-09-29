import time
from pathlib import Path
from typing import Any

import httpx

from openhands.sdk.conversation.system_mixins.base import SystemMixin
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


class RemoteSystemMixin(SystemMixin):
    """Mixin providing remote system operations.

    This mixin implements system operations for remote environments where
    the conversation communicates with a remote agent server. Operations
    are performed via HTTP API calls to the remote system.

    These operations are independent of the conversation and represent
    remote system access. They can be scoped to a workspace in the future
    if needed.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the remote system mixin.

        Requires _client and _id attributes to be available from the
        conversation implementation.
        """
        super().__init__(*args, **kwargs)

    @property
    def _http_client(self) -> httpx.Client:
        """Get the HTTP client for remote operations.

        This property should be implemented by the conversation class
        that uses this mixin.
        """
        if not hasattr(self, "_client"):
            raise AttributeError(
                "RemoteSystemMixin requires _client attribute to be set"
            )
        return self._client  # type: ignore

    @property
    def _conversation_id(self) -> str:
        """Get the conversation ID for remote operations.

        This property should be implemented by the conversation class
        that uses this mixin.
        """
        if not hasattr(self, "_id"):
            raise AttributeError("RemoteSystemMixin requires _id attribute to be set")
        return str(self._id)  # type: ignore

    def execute_command(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a bash command on the remote system.

        This method starts a bash command via the remote agent server API,
        then polls for the output until the command completes.

        Args:
            command: The bash command to execute
            cwd: Working directory (optional)
            timeout: Timeout in seconds

        Returns:
            dict: Result with stdout, stderr, exit_code, and other metadata
        """
        logger.debug(f"Executing remote command: {command}")

        # Step 1: Start the bash command
        payload = {
            "command": command,
            "timeout": int(timeout),
        }
        if cwd is not None:
            payload["cwd"] = str(cwd)

        try:
            # Start the command
            response = self._http_client.post(
                "/api/bash/execute_bash_command",
                json=payload,
                timeout=timeout + 5.0,  # Add buffer to HTTP timeout
            )
            response.raise_for_status()
            bash_command = response.json()
            command_id = bash_command["id"]

            logger.debug(f"Started command with ID: {command_id}")

            # Step 2: Poll for output until command completes
            start_time = time.time()
            stdout_parts = []
            stderr_parts = []
            exit_code = None

            while time.time() - start_time < timeout:
                # Search for all events and filter client-side
                # (workaround for bash service filtering bug)
                search_response = self._http_client.get(
                    "/api/bash/bash_events/search",
                    params={
                        "sort_order": "TIMESTAMP",
                        "limit": 100,
                    },
                    timeout=10.0,
                )
                search_response.raise_for_status()
                search_result = search_response.json()

                # Filter for BashOutput events for this command
                for event in search_result.get("items", []):
                    if (
                        event.get("kind") == "BashOutput"
                        and event.get("command_id") == command_id
                    ):
                        if event.get("stdout"):
                            stdout_parts.append(event["stdout"])
                        if event.get("stderr"):
                            stderr_parts.append(event["stderr"])
                        if event.get("exit_code") is not None:
                            exit_code = event["exit_code"]

                # If we have an exit code, the command is complete
                if exit_code is not None:
                    break

                # Wait a bit before polling again
                time.sleep(0.1)

            # If we timed out waiting for completion
            if exit_code is None:
                logger.warning(f"Command timed out after {timeout} seconds: {command}")
                exit_code = -1
                stderr_parts.append(f"Command timed out after {timeout} seconds")

            # Combine all output parts
            stdout = "".join(stdout_parts)
            stderr = "".join(stderr_parts)

            return {
                "command": command,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "timeout_occurred": exit_code == -1 and "timed out" in stderr,
            }

        except Exception as e:
            logger.error(f"Remote command execution failed: {e}")
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Remote execution error: {str(e)}",
                "timeout_occurred": False,
            }

    def execute_bash(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a bash command on the remote system.

        Sends the command to the remote agent server via HTTP API and
        returns the execution result.

        Args:
            command: The bash command to execute
            cwd: Working directory (optional)
            timeout: Timeout in seconds

        Returns:
            dict: Result with stdout, stderr, exit_code, and other metadata
        """
        logger.debug(f"Executing remote bash command: {command}")

        payload = {
            "command": command,
            "timeout": timeout,
        }
        if cwd is not None:
            payload["cwd"] = str(cwd)

        try:
            # Make synchronous HTTP call
            response = self._http_client.post(
                "/api/bash/execute",
                json=payload,
                timeout=timeout + 5.0,  # Add buffer to HTTP timeout
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Remote bash execution failed: {e}")
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Remote execution error: {str(e)}",
                "timeout_occurred": False,
            }

    def file_upload(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Upload a file to the remote system.

        Reads the local file and sends it to the remote system via HTTP API.

        Args:
            source_path: Path to the local source file
            destination_path: Path where the file should be uploaded on remote system

        Returns:
            dict: Result with success status and metadata
        """
        source = Path(source_path)
        destination = Path(destination_path)

        logger.debug(f"Remote file upload: {source} -> {destination}")

        try:
            # Read the file content
            with open(source, "rb") as f:
                file_content = f.read()

            # Prepare the upload
            files = {"file": (source.name, file_content)}
            data = {"destination_path": str(destination)}

            # Make synchronous HTTP call
            response = self._http_client.post(
                "/api/files/upload",
                files=files,
                data=data,
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Remote file upload failed: {e}")
            return {
                "success": False,
                "source_path": str(source),
                "destination_path": str(destination),
                "error": str(e),
            }

    def file_download(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Download a file from the remote system.

        Requests the file from the remote system via HTTP API and saves it locally.

        Args:
            source_path: Path to the source file on remote system
            destination_path: Path where the file should be saved locally

        Returns:
            dict: Result with success status and metadata
        """
        source = Path(source_path)
        destination = Path(destination_path)

        logger.debug(f"Remote file download: {source} -> {destination}")

        try:
            # Request the file from remote system
            params = {"file_path": str(source)}

            # Make synchronous HTTP call
            response = self._http_client.get(
                "/api/files/download",
                params=params,
                timeout=60.0,
            )
            response.raise_for_status()

            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Write the file content
            with open(destination, "wb") as f:
                f.write(response.content)

            return {
                "success": True,
                "source_path": str(source),
                "destination_path": str(destination),
                "file_size": len(response.content),
            }

        except Exception as e:
            logger.error(f"Remote file download failed: {e}")
            return {
                "success": False,
                "source_path": str(source),
                "destination_path": str(destination),
                "error": str(e),
            }
