"""Fixtures for file viewer tool tests."""

import tempfile
from pathlib import Path

import pytest

from openhands.tools.file_viewer.impl import FileViewerExecutor


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)

        # Create test directory structure
        (workspace / "subdir").mkdir()
        (workspace / "empty_dir").mkdir()

        # Create test files
        (workspace / "test.txt").write_text("Hello, World!\nThis is a test file.")
        (workspace / "subdir" / "nested.py").write_text("print('nested file')")
        (workspace / "large_file.txt").write_text(
            "".join(f"Line {i}\n" for i in range(100))
        )

        yield workspace


@pytest.fixture
def file_viewer_executor(temp_workspace):
    """Create a FileViewerExecutor for testing."""
    return FileViewerExecutor(workspace_root=str(temp_workspace))
