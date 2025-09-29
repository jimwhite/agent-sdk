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
