"""Tests for workspace boundary restrictions in FileEditor."""

import tempfile
from pathlib import Path

import pytest

from openhands.tools.str_replace_editor.editor import FileEditor
from openhands.tools.str_replace_editor.exceptions import (
    EditorToolParameterInvalidError,
)


def test_workspace_boundary_view_outside_workspace(tmp_path):
    """Test that viewing paths outside workspace is blocked when workspace_root is set."""  # noqa: E501
    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Create a file inside the workspace
    test_file = workspace_root / "test.txt"
    test_file.write_text("This is inside workspace")

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that accessing root directory is blocked
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(command="view", path="/")

    error_message = str(exc_info.value.message)
    assert "Access denied" in error_message
    assert "outside the allowed workspace directory" in error_message
    assert str(workspace_root) in error_message


def test_workspace_boundary_view_parent_directory(tmp_path):
    """Test that viewing parent directories outside workspace is blocked."""
    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that accessing parent directory is blocked
    parent_path = workspace_root.parent
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(command="view", path=str(parent_path))

    error_message = str(exc_info.value.message)
    assert "Access denied" in error_message
    assert "outside the allowed workspace directory" in error_message


def test_workspace_boundary_view_inside_workspace_allowed(tmp_path):
    """Test that viewing paths inside workspace is allowed."""
    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Create a subdirectory and file inside the workspace
    subdir = workspace_root / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_file.write_text("This is inside workspace")

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that accessing workspace root is allowed
    result = editor(command="view", path=str(workspace_root))
    assert not result.error  # error should be None or empty string
    assert "subdir/" in result.output

    # Test that accessing subdirectory is allowed
    result = editor(command="view", path=str(subdir))
    assert not result.error  # error should be None or empty string
    assert "test.txt" in result.output

    # Test that accessing file inside workspace is allowed
    result = editor(command="view", path=str(test_file))
    assert not result.error  # error should be None or empty string
    assert "This is inside workspace" in result.output


def test_workspace_boundary_create_outside_workspace(tmp_path):
    """Test that creating files outside workspace is blocked."""
    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that creating file outside workspace is blocked
    outside_file = tmp_path / "outside.txt"
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(command="create", path=str(outside_file), file_text="content")

    error_message = str(exc_info.value.message)
    assert "Access denied" in error_message
    assert "outside the allowed workspace directory" in error_message


def test_workspace_boundary_str_replace_outside_workspace(tmp_path):
    """Test that editing files outside workspace is blocked."""
    # Create a file outside the workspace
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("original content")

    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that editing file outside workspace is blocked
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(
            command="str_replace",
            path=str(outside_file),
            old_str="original",
            new_str="modified",
        )

    error_message = str(exc_info.value.message)
    assert "Access denied" in error_message
    assert "outside the allowed workspace directory" in error_message


def test_workspace_boundary_symlink_outside_workspace(tmp_path):
    """Test that symlinks pointing outside workspace are blocked."""
    # Create a file outside the workspace
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside content")

    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Create a symlink inside workspace pointing to outside file
    symlink_path = workspace_root / "symlink.txt"
    symlink_path.symlink_to(outside_file)

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that accessing symlink pointing outside workspace is blocked
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(command="view", path=str(symlink_path))

    error_message = str(exc_info.value.message)
    assert "Access denied" in error_message
    assert "outside the allowed workspace directory" in error_message


def test_workspace_boundary_no_workspace_root_allows_all(tmp_path):
    """Test that when no workspace_root is set, all paths are allowed."""
    # Create a file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Initialize editor without workspace_root
    editor = FileEditor()

    # Test that accessing any absolute path is allowed
    result = editor(command="view", path=str(test_file))
    assert not result.error  # error should be None or empty string
    assert "test content" in result.output


def test_workspace_boundary_with_dot_dot_path(tmp_path):
    """Test that paths with .. components outside workspace are blocked."""
    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Create a subdirectory inside workspace
    subdir = workspace_root / "subdir"
    subdir.mkdir()

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that accessing parent via .. is blocked when it goes outside workspace
    parent_via_dotdot = subdir / ".." / ".."
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(command="view", path=str(parent_via_dotdot))

    error_message = str(exc_info.value.message)
    assert "Access denied" in error_message
    assert "outside the allowed workspace directory" in error_message


def test_workspace_boundary_with_dot_dot_path_inside_workspace(tmp_path):
    """Test that paths with .. components inside workspace are allowed."""
    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Create nested directories inside workspace
    subdir1 = workspace_root / "subdir1"
    subdir1.mkdir()
    subdir2 = workspace_root / "subdir2"
    subdir2.mkdir()
    test_file = subdir2 / "test.txt"
    test_file.write_text("test content")

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that accessing sibling directory via .. is allowed when it stays inside workspace  # noqa: E501
    sibling_via_dotdot = subdir1 / ".." / "subdir2" / "test.txt"
    result = editor(command="view", path=str(sibling_via_dotdot))
    assert not result.error  # error should be None or empty string
    assert "test content" in result.output


def test_workspace_boundary_temp_directory_access():
    """Test that accessing system temp directory is blocked when workspace is set."""
    with tempfile.TemporaryDirectory() as workspace_root:
        # Initialize editor with workspace_root
        editor = FileEditor(workspace_root=workspace_root)

        # Test that accessing system temp directory is blocked
        system_temp = Path(tempfile.gettempdir())
        if system_temp != Path(workspace_root):
            with pytest.raises(EditorToolParameterInvalidError) as exc_info:
                editor(command="view", path=str(system_temp))

            error_message = str(exc_info.value.message)
            assert "Access denied" in error_message
            assert "outside the allowed workspace directory" in error_message


def test_workspace_boundary_home_directory_access(tmp_path):
    """Test that accessing home directory is blocked when workspace is set."""
    # Create a workspace root
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Initialize editor with workspace_root
    editor = FileEditor(workspace_root=str(workspace_root))

    # Test that accessing home directory is blocked
    home_dir = Path.home()
    if home_dir != workspace_root:
        with pytest.raises(EditorToolParameterInvalidError) as exc_info:
            editor(command="view", path=str(home_dir))

        error_message = str(exc_info.value.message)
        assert "Access denied" in error_message
        assert "outside the allowed workspace directory" in error_message
