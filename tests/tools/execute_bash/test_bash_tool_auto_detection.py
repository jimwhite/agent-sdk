"""Tests for BashTool auto-detection functionality."""

import tempfile
import uuid
from unittest.mock import patch

from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.conversation.state import ConversationState
from openhands.sdk.llm import LLM
from openhands.sdk.workspace import LocalWorkspace
from openhands.tools.execute_bash import BashTool
from openhands.tools.execute_bash.definition import ExecuteBashAction
from openhands.tools.execute_bash.impl import BashExecutor
from openhands.tools.execute_bash.terminal import (
    SubprocessTerminal,
    TerminalSession,
    TmuxTerminal,
)


def _create_conv_state(working_dir: str) -> ConversationState:
    """Helper to create a ConversationState for testing."""
    llm = LLM(model="gpt-4o-mini", api_key=SecretStr("test-key"), usage_id="test-llm")
    agent = Agent(llm=llm, tools=[])
    return ConversationState.create(
        id=uuid.uuid4(),
        agent=agent,
        workspace=LocalWorkspace(working_dir=working_dir),
    )


def test_default_auto_detection():
    """Test that BashTool auto-detects the appropriate session type."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tools = BashTool.create(_create_conv_state(temp_dir))
        tool = tools[0]

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
        action = ExecuteBashAction(command="echo 'Auto-detection test'")
        obs = executor(action)
        assert "Auto-detection test" in obs.output


def test_forced_terminal_types():
    """Test forcing specific session types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Test forced subprocess session
        tools = BashTool.create(
            _create_conv_state(temp_dir), terminal_type="subprocess"
        )
        tool = tools[0]
        assert tool.executor is not None
        executor = tool.executor
        assert isinstance(executor, BashExecutor)
        assert isinstance(executor.session, TerminalSession)
        assert isinstance(executor.session.terminal, SubprocessTerminal)

        # Test basic functionality
        action = ExecuteBashAction(command="echo 'Subprocess test'")
        obs = tool.executor(action)
        assert obs.metadata.exit_code == 0


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
            tools = BashTool.create(_create_conv_state(temp_dir))
            tool = tools[0]
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
            tools = BashTool.create(_create_conv_state(temp_dir))
            tool = tools[0]
            assert tool.executor is not None
            executor = tool.executor
            assert isinstance(executor, BashExecutor)
            assert isinstance(executor.session, TerminalSession)
            assert isinstance(executor.session.terminal, SubprocessTerminal)


def test_session_parameters():
    """Test that session parameters are properly passed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tools = BashTool.create(
            _create_conv_state(temp_dir),
            username="testuser",
            no_change_timeout_seconds=60,
            terminal_type="subprocess",
        )
        tool = tools[0]

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
        tools = BashTool.create(_create_conv_state(temp_dir))
        tool = tools[0]

        assert tool.executor is not None
        action = ExecuteBashAction(command="echo 'Backward compatibility test'")
        obs = tool.executor(action)
        assert "Backward compatibility test" in obs.output
        assert obs.metadata.exit_code == 0


def test_tool_metadata():
    """Test that tool metadata is preserved."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tools = BashTool.create(_create_conv_state(temp_dir))
        tool = tools[0]

        assert tool.name == "execute_bash"
        assert tool.description is not None
        assert tool.action_type == ExecuteBashAction
        assert hasattr(tool, "annotations")


def test_session_lifecycle():
    """Test session lifecycle management."""
    with tempfile.TemporaryDirectory() as temp_dir:
        tools = BashTool.create(
            _create_conv_state(temp_dir), terminal_type="subprocess"
        )
        tool = tools[0]

        # Session should be initialized
        assert tool.executor is not None
        executor = tool.executor
        assert isinstance(executor, BashExecutor)
        assert executor.session._initialized

        # Should be able to execute commands
        action = ExecuteBashAction(command="echo 'Lifecycle test'")
        obs = executor(action)
        assert obs.metadata.exit_code == 0

        # Manual cleanup should work
        executor.session.close()
        assert executor.session._closed
