"""Tests for BashTool auto-detection functionality."""

import tempfile
from unittest.mock import patch

from openhands.sdk.tool import SchemaInstance
from openhands.tools.execute_bash import BashTool
from openhands.tools.execute_bash.impl import BashExecutor
from openhands.tools.execute_bash.terminal import (
    SubprocessTerminal,
    TerminalSession,
    TmuxTerminal,
)


def test_default_auto_detection():
    """Test that BashTool auto-detects the appropriate session type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tool = BashTool.create(working_dir=temp_dir)

        # BashTool always has an executor
        assert tool.executor is not None
        executor = tool.executor
        assert isinstance(executor, BashExecutor)

        # Should always use TerminalSession now
        assert isinstance(executor.session, TerminalSession)

        # Check that the terminal backend is appropriate
        terminal_type = type(executor.session.terminal).__name__
        assert terminal_type in ["TmuxTerminal", "SubprocessTerminal"]

        # Test that it works
        action = SchemaInstance(
            name="ExecuteBashAction",
            definition=tool.input_schema,
            data={"command": "echo 'Auto-detection test'"},
        )
        obs = executor(action)
        assert "Auto-detection test" in obs.data["output"]


def test_forced_terminal_types():
    """Test forcing specific session types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test forced subprocess session
        tool = BashTool.create(working_dir=temp_dir, terminal_type="subprocess")
        assert tool.executor is not None
        executor = tool.executor
        assert isinstance(executor, BashExecutor)
        assert isinstance(executor.session, TerminalSession)
        assert isinstance(executor.session.terminal, SubprocessTerminal)

        # Test basic functionality
        action = SchemaInstance(
            name="ExecuteBashAction",
            definition=tool.input_schema,
            data={"command": "echo 'Subprocess test'"},
        )
        obs = tool.executor(action)
        assert obs.data["metadata"]["exit_code"] == 0


@patch("platform.system")
def test_unix_auto_detection(mock_system):
    """Test auto-detection behavior on Unix-like systems."""
    mock_system.return_value = "Linux"

    with tempfile.TemporaryDirectory() as temp_dir:
        # Mock tmux as available
        with patch(
            "openhands.tools.execute_bash.terminal.factory._is_tmux_available",
            return_value=True,
        ):
            tool = BashTool.create(working_dir=temp_dir)
            assert tool.executor is not None
            executor = tool.executor
            assert isinstance(executor, BashExecutor)
            assert isinstance(executor.session, TerminalSession)
            assert isinstance(executor.session.terminal, TmuxTerminal)

        # Mock tmux as unavailable
        with patch(
            "openhands.tools.execute_bash.terminal.factory._is_tmux_available",
            return_value=False,
        ):
            tool = BashTool.create(working_dir=temp_dir)
            assert tool.executor is not None
            executor = tool.executor
            assert isinstance(executor, BashExecutor)
            assert isinstance(executor.session, TerminalSession)
            assert isinstance(executor.session.terminal, SubprocessTerminal)


def test_session_parameters():
    """Test that session parameters are properly passed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tool = BashTool.create(
            working_dir=temp_dir,
            username="testuser",
            no_change_timeout_seconds=60,
            terminal_type="subprocess",
        )

        assert tool.executor is not None
        executor = tool.executor
        assert isinstance(executor, BashExecutor)
        session = executor.session
        assert session.work_dir == temp_dir
        assert session.username == "testuser"
        assert session.no_change_timeout_seconds == 60


def test_backward_compatibility():
    """Test that the simplified API still works."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # This should work just like before
        tool = BashTool.create(working_dir=temp_dir)

        assert tool.executor is not None
        action = SchemaInstance(
            name="ExecuteBashAction",
            definition=tool.input_schema,
            data={"command": "echo 'Backward compatibility test'"},
        )
        obs = tool.executor(action)
        assert "Backward compatibility test" in obs.data["output"]
        assert obs.data["metadata"]["exit_code"] == 0


def test_tool_metadata():
    """Test that tool metadata is preserved."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tool = BashTool.create(working_dir=temp_dir)

        assert tool.name == "execute_bash"
        assert tool.description is not None
        assert tool.input_schema is not None
        assert tool.annotations is not None


def test_session_lifecycle():
    """Test session lifecycle management."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tool = BashTool.create(working_dir=temp_dir, terminal_type="subprocess")

        # Session should be initialized
        assert tool.executor is not None
        executor = tool.executor
        assert isinstance(executor, BashExecutor)
        assert executor.session._initialized

        # Should be able to execute commands
        action = SchemaInstance(
            name="ExecuteBashAction",
            definition=tool.input_schema,
            data={"command": "echo 'Lifecycle test'"},
        )
        obs = executor(action)
        assert obs.data["metadata"]["exit_code"] == 0

        # Manual cleanup should work
        executor.session.close()
        assert executor.session._closed
