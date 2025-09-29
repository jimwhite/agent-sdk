import shutil
from pathlib import Path
from typing import Any

from openhands.sdk.conversation.system_mixins.base import SystemMixin
from openhands.sdk.logger import get_logger
from openhands.sdk.utils.command import execute_command


logger = get_logger(__name__)


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

    def execute_command(
        self,
        command: str,
        cwd: str | Path,
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
        logger.debug(f"Executing local bash command: {command} in {cwd}")
        result = execute_command(
            command,
            cwd=str(cwd),
            timeout=timeout,
            print_output=True,
        )
        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout_occurred": result.returncode == -1,
        }

    def file_upload(
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

    def file_download(
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
