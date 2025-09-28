"""System mixins for conversation implementations.

These mixins provide system-level functionality (shell execution, file operations)
that are independent of the conversation itself. A system can spawn multiple
conversations, and these functionalities can be accessed without connecting to
a system. The reason these methods are tied to conversation is mostly for
convenience, and maybe later they will be scoped based on the workspace of
the conversation.

The mixins are designed to be composable and reusable across different
conversation implementations.
"""

import asyncio
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import httpx

from openhands.sdk.logger import get_logger
from openhands.sdk.utils.shell_execution import (
    execute_shell_command,
)


logger = get_logger(__name__)


class SystemMixin(ABC):
    """Abstract base mixin for system-level operations.

    This mixin defines the interface for system operations that should be
    available on conversation objects. These operations are independent of
    the conversation itself and represent system-level capabilities.

    The reason these methods are provided as a mixin rather than directly
    in the conversation class is to maintain separation of concerns and
    allow for different implementations (local vs remote systems).
    """

    @abstractmethod
    async def execute_bash(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a bash command on the system.

        Args:
            command: The bash command to execute
            cwd: Working directory for the command (optional)
            timeout: Timeout in seconds (defaults to 30.0)

        Returns:
            dict: Result containing stdout, stderr, exit_code, and other metadata

        Raises:
            Exception: If command execution fails
        """
        ...

    @abstractmethod
    async def file_upload(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Upload a file to the system.

        Args:
            source_path: Path to the source file
            destination_path: Path where the file should be uploaded

        Returns:
            dict: Result containing success status and metadata

        Raises:
            Exception: If file upload fails
        """
        ...

    @abstractmethod
    async def file_download(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Download a file from the system.

        Args:
            source_path: Path to the source file on the system
            destination_path: Path where the file should be downloaded

        Returns:
            dict: Result containing success status and metadata

        Raises:
            Exception: If file download fails
        """
        ...


class LocalSystemMixin(SystemMixin):
    """Mixin providing local system operations.

    This mixin implements system operations for local environments where
    the conversation is running on the same system as the operations.
    File operations use shutil.copy for efficiency, and shell execution
    uses the shared shell execution utility.

    These operations are independent of the conversation and represent
    direct system access. They can be scoped to a workspace in the future
    if needed.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the local system mixin.

        The working directory defaults to the current directory but can be
        overridden by subclasses or through configuration.
        """
        super().__init__(*args, **kwargs)
        self._working_dir: Path | None = None

    @property
    def working_dir(self) -> Path:
        """Get the working directory for system operations."""
        if self._working_dir is None:
            return Path.cwd()
        return self._working_dir

    @working_dir.setter
    def working_dir(self, value: str | Path) -> None:
        """Set the working directory for system operations."""
        self._working_dir = Path(value)

    async def execute_bash(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a bash command locally.

        Uses the shared shell execution utility to run commands with proper
        timeout handling, output streaming, and error management.

        Args:
            command: The bash command to execute
            cwd: Working directory (defaults to self.working_dir)
            timeout: Timeout in seconds

        Returns:
            dict: Result with stdout, stderr, exit_code, command, and timeout_occurred
        """
        if cwd is None:
            cwd = self.working_dir

        logger.debug(f"Executing local bash command: {command} in {cwd}")

        result = await execute_shell_command(
            command=command,
            cwd=cwd,
            timeout=timeout,
        )

        return {
            "command": result.command,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout_occurred": result.timeout_occurred,
        }

    async def file_upload(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Upload (copy) a file locally.

        For local systems, file upload is implemented as a file copy operation
        using shutil.copy2 to preserve metadata.

        Args:
            source_path: Path to the source file
            destination_path: Path where the file should be copied

        Returns:
            dict: Result with success status and file information
        """
        source = Path(source_path)
        destination = Path(destination_path)

        logger.debug(f"Local file upload: {source} -> {destination}")

        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file with metadata preservation
            shutil.copy2(source, destination)

            return {
                "success": True,
                "source_path": str(source),
                "destination_path": str(destination),
                "file_size": destination.stat().st_size,
            }

        except Exception as e:
            logger.error(f"Local file upload failed: {e}")
            return {
                "success": False,
                "source_path": str(source),
                "destination_path": str(destination),
                "error": str(e),
            }

    async def file_download(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Download (copy) a file locally.

        For local systems, file download is implemented as a file copy operation
        using shutil.copy2 to preserve metadata.

        Args:
            source_path: Path to the source file
            destination_path: Path where the file should be copied

        Returns:
            dict: Result with success status and file information
        """
        source = Path(source_path)
        destination = Path(destination_path)

        logger.debug(f"Local file download: {source} -> {destination}")

        try:
            # Ensure destination directory exists
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy the file with metadata preservation
            shutil.copy2(source, destination)

            return {
                "success": True,
                "source_path": str(source),
                "destination_path": str(destination),
                "file_size": destination.stat().st_size,
            }

        except Exception as e:
            logger.error(f"Local file download failed: {e}")
            return {
                "success": False,
                "source_path": str(source),
                "destination_path": str(destination),
                "error": str(e),
            }


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

    async def execute_bash(
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
            # Use asyncio to run the synchronous HTTP call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._http_client.post(
                    "/api/bash/execute",
                    json=payload,
                    timeout=timeout + 5.0,  # Add buffer to HTTP timeout
                ),
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

    async def file_upload(
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

            # Use asyncio to run the synchronous HTTP call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._http_client.post(
                    "/api/files/upload",
                    files=files,
                    data=data,
                    timeout=60.0,
                ),
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

    async def file_download(
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

            # Use asyncio to run the synchronous HTTP call
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._http_client.get(
                    "/api/files/download",
                    params=params,
                    timeout=60.0,
                ),
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
