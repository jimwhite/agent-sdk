"""Tests for FileViewerTool functionality."""

from openhands.tools.file_viewer.definition import (
    FileViewerAction,
    FileViewerObservation,
)


def test_view_file_success(file_viewer_executor, temp_workspace):
    """Test successful file viewing."""
    action = FileViewerAction(command="view", path="test.txt")
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.command == "view"
    assert result.path is not None and result.path.endswith("test.txt")
    assert result.error is None
    assert "Hello, World!" in result.output
    assert "This is a test file." in result.output


def test_view_file_with_range(file_viewer_executor, temp_workspace):
    """Test file viewing with line range."""
    action = FileViewerAction(command="view", path="test.txt", view_range=[1, 1])
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is None
    assert "Hello, World!" in result.output
    assert "This is a test file." not in result.output


def test_view_nonexistent_file(file_viewer_executor):
    """Test viewing a file that doesn't exist."""
    action = FileViewerAction(command="view", path="nonexistent.txt")
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is not None
    assert "not found" in result.error


def test_list_directory(file_viewer_executor, temp_workspace):
    """Test directory listing."""
    action = FileViewerAction(command="list", path=".")
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.command == "list"
    assert result.error is None
    assert "test.txt" in result.output
    assert "subdir/" in result.output
    assert "empty_dir/" in result.output


def test_list_subdirectory(file_viewer_executor, temp_workspace):
    """Test listing a subdirectory."""
    action = FileViewerAction(command="list", path="subdir")
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is None
    assert "nested.py" in result.output


def test_list_nonexistent_directory(file_viewer_executor):
    """Test listing a directory that doesn't exist."""
    action = FileViewerAction(command="list", path="nonexistent_dir")
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is not None
    assert "not found" in result.error


def test_path_traversal_protection(file_viewer_executor):
    """Test that path traversal attacks are blocked."""
    action = FileViewerAction(command="view", path="../../../etc/passwd")
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is not None
    assert "outside workspace" in result.error


def test_invalid_command(file_viewer_executor):
    """Test handling of invalid commands."""

    # Since Pydantic validates the command field, we need to test this at the
    # executor level
    # We'll create a mock action object that bypasses Pydantic validation
    class MockAction:
        def __init__(self):
            self.command = "delete"
            self.path = "test.txt"
            self.view_range = None

    mock_action = MockAction()
    result = file_viewer_executor(mock_action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is not None
    assert "Unknown command" in result.error


def test_view_range_validation(file_viewer_executor, temp_workspace):
    """Test view range validation."""
    # Invalid range (start > end)
    action = FileViewerAction(command="view", path="test.txt", view_range=[2, 1])
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is not None
    assert "Invalid view_range" in result.error


def test_view_range_out_of_bounds(file_viewer_executor, temp_workspace):
    """Test view range that exceeds file length."""
    action = FileViewerAction(command="view", path="test.txt", view_range=[1, 100])
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is None  # Should not error, just show available lines
    assert "Hello, World!" in result.output


def test_empty_directory_listing(file_viewer_executor, temp_workspace):
    """Test listing an empty directory."""
    action = FileViewerAction(command="list", path="empty_dir")
    result = file_viewer_executor(action)

    assert isinstance(result, FileViewerObservation)
    assert result.error is None
    assert "empty" in result.output.lower() or result.output.strip() == ""
