"""Tests for LocalWorkspace implementation."""

import tempfile
from pathlib import Path

from openhands.workspace import LocalWorkspace


def test_local_workspace_creation():
    """Test LocalWorkspace can be created."""
    workspace = LocalWorkspace(working_dir="/tmp")
    assert workspace.working_dir == "/tmp"
    assert workspace.is_local() is True


def test_local_workspace_execute_command():
    """Test LocalWorkspace can execute commands."""
    workspace = LocalWorkspace(working_dir="/tmp")
    result = workspace.execute_command("echo 'hello world'")

    assert result.exit_code == 0
    assert "hello world" in result.stdout
    assert result.command == "echo 'hello world'"
    assert result.timeout_occurred is False


def test_local_workspace_file_operations():
    """Test LocalWorkspace file upload and download."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = LocalWorkspace(working_dir=temp_dir)

        # Create a test file
        source_file = Path(temp_dir) / "source.txt"
        source_file.write_text("test content")

        # Test file upload (copy)
        dest_file = Path(temp_dir) / "dest.txt"
        result = workspace.file_upload(source_file, dest_file)

        assert result.success is True
        assert result.source_path == str(source_file)
        assert result.destination_path == str(dest_file)
        assert dest_file.exists()
        assert dest_file.read_text() == "test content"

        # Test file download (copy)
        download_file = Path(temp_dir) / "download.txt"
        result = workspace.file_download(dest_file, download_file)

        assert result.success is True
        assert result.source_path == str(dest_file)
        assert result.destination_path == str(download_file)
        assert download_file.exists()
        assert download_file.read_text() == "test content"


def test_local_workspace_context_manager():
    """Test LocalWorkspace works as context manager."""
    with LocalWorkspace(working_dir="/tmp") as workspace:
        assert workspace.working_dir == "/tmp"
        result = workspace.execute_command("echo 'context test'")
        assert result.exit_code == 0
