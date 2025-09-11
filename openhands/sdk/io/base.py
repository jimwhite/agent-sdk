"""Base file storage interface."""

from abc import abstractmethod


class FileStore:
    """Abstract base class for file storage operations."""

    @abstractmethod
    def write(self, path: str, contents: str | bytes) -> None:
        """Write contents to a file at the specified path."""
        pass

    @abstractmethod
    def read(self, path: str) -> str:
        """Read contents from a file at the specified path."""
        pass

    @abstractmethod
    def list(self, path: str) -> list[str]:
        """List files and directories at the specified path."""
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete a file or directory at the specified path."""
        pass
