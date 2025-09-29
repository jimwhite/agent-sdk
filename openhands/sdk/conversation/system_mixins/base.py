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

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from openhands.sdk.logger import get_logger


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
    def execute_bash(
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
    def file_upload(
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
    def file_download(
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
