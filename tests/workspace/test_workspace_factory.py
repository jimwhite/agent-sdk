"""Tests for Workspace factory."""

from openhands.workspace import LocalWorkspace, RemoteWorkspace, Workspace


def test_workspace_factory_local():
    """Test Workspace factory creates LocalWorkspace when no host provided."""
    workspace = Workspace(working_dir="/tmp")
    assert isinstance(workspace, LocalWorkspace)
    assert workspace.working_dir == "/tmp"
    assert workspace.is_remote() is False


def test_workspace_factory_remote():
    """Test Workspace factory creates RemoteWorkspace when host provided."""
    workspace = Workspace(working_dir="/tmp", host="http://localhost:8000")
    assert isinstance(workspace, RemoteWorkspace)
    assert workspace.working_dir == "/tmp"
    assert workspace.host == "http://localhost:8000"
    assert workspace.is_remote() is True


def test_workspace_factory_remote_with_api_key():
    """Test Workspace factory creates RemoteWorkspace with API key."""
    workspace = Workspace(
        working_dir="/tmp", host="http://localhost:8000", api_key="test-key"
    )
    assert isinstance(workspace, RemoteWorkspace)
    assert workspace.working_dir == "/tmp"
    assert workspace.host == "http://localhost:8000"
    assert workspace.api_key == "test-key"
    assert workspace.is_remote() is True
