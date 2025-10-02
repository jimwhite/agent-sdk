"""Implementation of the read-only file viewer tool."""

from pathlib import Path

from openhands.sdk.logger import get_logger
from openhands.sdk.tool import ToolExecutor
from openhands.tools.file_viewer.definition import (
    FileViewerAction,
    FileViewerObservation,
)


logger = get_logger(__name__)


class FileViewerExecutor(ToolExecutor):
    """Executor for read-only file viewing operations."""

    def __init__(self, workspace_root: str):
        """Initialize the FileViewerExecutor.

        Args:
            workspace_root: Root directory for file operations.
        """
        self.workspace_root = Path(workspace_root).resolve()
        logger.info(
            f"FileViewerExecutor initialized with workspace: {self.workspace_root}"
        )

    def __call__(self, action: FileViewerAction) -> FileViewerObservation:
        """Execute the file viewer action."""
        try:
            # Resolve path relative to workspace root
            if Path(action.path).is_absolute():
                path = Path(action.path).resolve()
            else:
                path = (self.workspace_root / action.path).resolve()

            # Security check: ensure path is within workspace
            if not str(path).startswith(str(self.workspace_root)):
                return FileViewerObservation(
                    command=action.command,
                    path=action.path,
                    error=(
                        f"Access denied: Path {action.path} is outside "
                        f"workspace {self.workspace_root}"
                    ),
                )

            if action.command == "view":
                return self._view_file(path, action.view_range)
            elif action.command == "list":
                return self._list_directory(path)
            else:
                return FileViewerObservation(
                    command="view",  # Use valid command for observation
                    path=action.path,
                    error=f"Unknown command: {action.command}",
                )

        except Exception as e:
            logger.error(f"Error in FileViewerExecutor: {e}")
            return FileViewerObservation(
                command=action.command,
                path=action.path,
                error=f"Error: {str(e)}",
            )

    def _view_file(
        self, path: Path, view_range: list[int] | None = None
    ) -> FileViewerObservation:
        """View the contents of a file."""
        if not path.exists():
            return FileViewerObservation(
                command="view",
                path=str(path),
                error=f"File not found: {path}",
            )

        if not path.is_file():
            return FileViewerObservation(
                command="view",
                path=str(path),
                error=f"Path is not a file: {path}",
            )

        try:
            # Check if file is binary
            with open(path, "rb") as f:
                chunk = f.read(1024)
                if b"\0" in chunk:
                    return FileViewerObservation(
                        command="view",
                        path=str(path),
                        output=(
                            f"Binary file: {path.name} "
                            f"(size: {path.stat().st_size} bytes)"
                        ),
                    )

            # Read text file
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            # Apply view range if specified
            if view_range:
                # Validate range
                if len(view_range) != 2:
                    return FileViewerObservation(
                        command="view",
                        path=str(path),
                        error="Invalid view_range: must contain exactly 2 elements",
                    )

                if view_range[1] != -1 and view_range[0] > view_range[1]:
                    return FileViewerObservation(
                        command="view",
                        path=str(path),
                        error=(
                            "Invalid view_range: start line cannot be greater "
                            "than end line"
                        ),
                    )

                start_line = max(1, view_range[0])
                end_line = (
                    len(lines)
                    if view_range[1] == -1
                    else min(len(lines), view_range[1])
                )

                if start_line > len(lines):
                    return FileViewerObservation(
                        command="view",
                        path=str(path),
                        error=(
                            f"Start line {start_line} exceeds file length {len(lines)}"
                        ),
                    )

                selected_lines = lines[start_line - 1 : end_line]
                output_lines = []
                for i, line in enumerate(selected_lines, start=start_line):
                    output_lines.append(f"{i:6d}\t{line.rstrip()}")

                output = f"File: {path}\nLines {start_line}-{end_line}:\n" + "\n".join(
                    output_lines
                )
            else:
                # Show entire file with line numbers
                output_lines = []
                for i, line in enumerate(lines, 1):
                    output_lines.append(f"{i:6d}\t{line.rstrip()}")

                output = f"File: {path}\n" + "\n".join(output_lines)

            return FileViewerObservation(
                command="view",
                path=str(path),
                output=output,
            )

        except UnicodeDecodeError:
            return FileViewerObservation(
                command="view",
                path=str(path),
                output=(
                    f"Binary or non-UTF-8 file: {path.name} "
                    f"(size: {path.stat().st_size} bytes)"
                ),
            )
        except Exception as e:
            return FileViewerObservation(
                command="view",
                path=str(path),
                error=f"Error reading file: {str(e)}",
            )

    def _list_directory(self, path: Path) -> FileViewerObservation:
        """List the contents of a directory."""
        if not path.exists():
            return FileViewerObservation(
                command="list",
                path=str(path),
                error=f"Directory not found: {path}",
            )

        if not path.is_dir():
            return FileViewerObservation(
                command="list",
                path=str(path),
                error=f"Path is not a directory: {path}",
            )

        try:
            output_lines = [f"Directory: {path}"]

            # Get all items in directory
            items = []
            for item in path.iterdir():
                if item.name.startswith("."):
                    continue  # Skip hidden files

                try:
                    stat = item.stat()
                    if item.is_dir():
                        items.append((item.name + "/", "dir", int(stat.st_size)))
                    else:
                        items.append((item.name, "file", int(stat.st_size)))
                except (OSError, PermissionError):
                    items.append((item.name, "unknown", 0))

            # Sort items: directories first, then files, both alphabetically
            items.sort(key=lambda x: (x[1] != "dir", x[0].lower()))

            if not items:
                output_lines.append("(empty directory)")
            else:
                for name, item_type, size in items:
                    if item_type == "dir":
                        output_lines.append(f"  📁 {name}")
                    elif item_type == "file":
                        size_str = self._format_size(size)
                        output_lines.append(f"  📄 {name} ({size_str})")
                    else:
                        output_lines.append(f"  ❓ {name}")

            # Show subdirectory contents (1 level deep) for better overview
            subdirs = [
                item
                for item in path.iterdir()
                if item.is_dir() and not item.name.startswith(".")
            ]
            if subdirs and len(subdirs) <= 5:  # Only show if not too many subdirs
                for subdir in sorted(subdirs)[:3]:  # Limit to first 3 subdirs
                    try:
                        sub_items = [
                            item
                            for item in subdir.iterdir()
                            if not item.name.startswith(".")
                        ]
                        if sub_items:
                            output_lines.append(f"\n  📁 {subdir.name}/:")
                            for sub_item in sorted(sub_items)[
                                :5
                            ]:  # Limit to first 5 items
                                if sub_item.is_dir():
                                    output_lines.append(f"    📁 {sub_item.name}/")
                                else:
                                    size_str = self._format_size(
                                        sub_item.stat().st_size
                                    )
                                    output_lines.append(
                                        f"    📄 {sub_item.name} ({size_str})"
                                    )
                            if len(sub_items) > 5:
                                output_lines.append(
                                    f"    ... and {len(sub_items) - 5} more items"
                                )
                    except (OSError, PermissionError):
                        continue

            return FileViewerObservation(
                command="list",
                path=str(path),
                output="\n".join(output_lines),
            )

        except Exception as e:
            return FileViewerObservation(
                command="list",
                path=str(path),
                error=f"Error listing directory: {str(e)}",
            )

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        size_float = float(size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size_float < 1024:
                return (
                    f"{size_float:.1f}{unit}"
                    if size_float != int(size_float)
                    else f"{int(size_float)}{unit}"
                )
            size_float /= 1024
        return f"{size_float:.1f}TB"
