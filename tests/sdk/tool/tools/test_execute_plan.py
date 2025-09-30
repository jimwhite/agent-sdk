"""Tests for execute_plan tool."""

import os
import tempfile
from unittest.mock import Mock, mock_open, patch

from openhands.sdk.llm.message import TextContent
from openhands.sdk.tool.tools.execute_plan import (
    ExecutePlanAction,
    ExecutePlanExecutor,
    ExecutePlanObservation,
    ExecutePlanTool,
)


def test_execute_plan_action():
    """Test ExecutePlanAction creation and properties."""
    action = ExecutePlanAction(plan_file="PLAN.md")

    assert action.plan_file == "PLAN.md"

    # Test default value
    action_default = ExecutePlanAction()
    assert action_default.plan_file == "PLAN.md"

    # Test visualization
    viz = action.visualize
    assert "Executing Plan" in str(viz)
    assert "PLAN.md" in str(viz)


def test_execute_plan_observation_success():
    """Test successful ExecutePlanObservation."""
    obs = ExecutePlanObservation(
        success=True,
        child_conversation_id="exec-123",
        message="Started execution",
        working_directory="/tmp/exec",
        plan_content="# Plan\n1. Step one\n2. Step two",
    )

    assert obs.success is True
    assert obs.child_conversation_id == "exec-123"
    assert obs.message == "Started execution"
    assert obs.working_directory == "/tmp/exec"
    assert obs.plan_content == "# Plan\n1. Step one\n2. Step two"
    assert obs.error is None

    # Test agent observation
    agent_obs = obs.agent_observation
    assert len(agent_obs) == 1
    assert isinstance(agent_obs[0], TextContent)
    assert "✅" in agent_obs[0].text
    assert "exec-123" in agent_obs[0].text

    # Test visualization
    viz = obs.visualize
    assert "✅" in str(viz)


def test_execute_plan_observation_failure():
    """Test failed ExecutePlanObservation."""
    obs = ExecutePlanObservation(
        success=False,
        message="",
        error="Plan file not found",
    )

    assert obs.success is False
    assert obs.error == "Plan file not found"

    # Test agent observation
    agent_obs = obs.agent_observation
    assert len(agent_obs) == 1
    assert isinstance(agent_obs[0], TextContent)
    assert "❌" in agent_obs[0].text
    assert "Plan file not found" in agent_obs[0].text

    # Test visualization
    viz = obs.visualize
    assert "❌" in str(viz)


def test_execute_plan_executor_no_conversation():
    """Test executor when no conversation is available."""
    executor = ExecutePlanExecutor()
    action = ExecutePlanAction(plan_file="PLAN.md")

    result = executor(action)

    assert result.success is False
    assert result.error is not None
    assert "No active conversation found" in result.error


def test_execute_plan_executor_file_not_found():
    """Test executor when plan file doesn't exist."""
    mock_conversation = Mock()
    mock_conversation._state.working_dir = "/tmp/test"

    executor = ExecutePlanExecutor()
    executor._conversation = mock_conversation  # type: ignore[attr-defined]

    action = ExecutePlanAction(plan_file="PLAN.md")

    with patch("os.path.exists", return_value=False):
        result = executor(action)

    assert result.success is False
    assert result.error is not None
    assert "Plan file PLAN.md not found" in result.error


def test_execute_plan_executor_empty_file():
    """Test executor when plan file is empty."""
    mock_conversation = Mock()
    mock_conversation._state.working_dir = "/tmp/test"

    executor = ExecutePlanExecutor()
    executor._conversation = mock_conversation  # type: ignore[attr-defined]

    action = ExecutePlanAction(plan_file="PLAN.md")

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data="")),
    ):
        result = executor(action)

    assert result.success is False
    assert result.error is not None
    assert "Plan file PLAN.md is empty" in result.error


@patch("openhands.sdk.agent.registry.AgentRegistry")
def test_execute_plan_executor_success(mock_registry_class):
    """Test successful execution of execute_plan."""
    # Setup mocks
    mock_llm = Mock()
    mock_agent = Mock()

    # Mock the registry instance
    mock_registry = Mock()
    mock_registry.create.return_value = mock_agent
    mock_registry_class.return_value = mock_registry

    mock_conversation = Mock()
    mock_conversation.agent.llm = mock_llm
    mock_conversation._state.working_dir = "/tmp/test"

    mock_child_conversation = Mock()
    mock_child_conversation._state.id = "exec-123"
    mock_child_conversation._state.working_dir = "/tmp/exec"
    mock_conversation.create_child_conversation.return_value = mock_child_conversation

    # Create executor and set conversation
    executor = ExecutePlanExecutor()
    executor._conversation = mock_conversation  # type: ignore[attr-defined]

    # Execute
    action = ExecutePlanAction(plan_file="PLAN.md")
    plan_content = "# Plan\n1. Step one\n2. Step two"

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=plan_content)),
    ):
        result = executor(action)

    # Verify
    assert result.success is True
    assert result.child_conversation_id == "exec-123"
    assert result.working_directory == "/tmp/exec"
    assert "Started execution of plan" in result.message
    assert result.plan_content == plan_content

    # Verify calls
    mock_registry.create.assert_called_once_with("execution", llm=mock_llm)
    mock_conversation.create_child_conversation.assert_called_once_with(
        agent=mock_agent, visualize=False
    )
    mock_child_conversation.send_message.assert_called_once()


@patch("openhands.sdk.agent.registry.AgentRegistry")
def test_execute_plan_executor_failure(mock_registry_class):
    """Test executor failure handling."""
    # Setup mocks to raise exception
    mock_registry = Mock()
    mock_registry.create.side_effect = Exception("Registry error")
    mock_registry_class.return_value = mock_registry

    mock_conversation = Mock()
    mock_conversation.agent.llm = Mock()
    mock_conversation._state.working_dir = "/tmp/test"

    # Create executor and set conversation
    executor = ExecutePlanExecutor()
    executor._conversation = mock_conversation  # type: ignore[attr-defined]

    # Execute
    action = ExecutePlanAction(plan_file="PLAN.md")
    plan_content = "# Plan\n1. Step one"

    with (
        patch("os.path.exists", return_value=True),
        patch("builtins.open", mock_open(read_data=plan_content)),
    ):
        result = executor(action)

    # Verify
    assert result.success is False
    assert result.error is not None
    assert "Failed to execute plan" in result.error
    assert "Registry error" in result.error


def test_execute_plan_tool_structure():
    """Test the tool structure and properties."""
    tool = ExecutePlanTool

    assert tool.name == "execute_plan"
    assert "execute the plan" in tool.description.lower()
    assert tool.action_type == ExecutePlanAction
    assert tool.observation_type == ExecutePlanObservation
    assert isinstance(tool.executor, ExecutePlanExecutor)

    # Test annotations
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is False
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is False
    assert tool.annotations.openWorldHint is True


def test_execute_plan_with_real_file():
    """Test executor with a real temporary file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a real plan file
        plan_file = os.path.join(temp_dir, "PLAN.md")
        plan_content = "# Test Plan\n1. First step\n2. Second step"

        with open(plan_file, "w") as f:
            f.write(plan_content)

        # Setup mocks
        mock_conversation = Mock()
        mock_conversation._state.working_dir = temp_dir
        mock_conversation._agent.llm = Mock()

        mock_child_conversation = Mock()
        mock_child_conversation._state.id = "exec-456"
        mock_child_conversation._state.working_dir = "/tmp/exec"
        mock_conversation.create_child_conversation.return_value = (
            mock_child_conversation
        )

        # Create executor and set conversation
        executor = ExecutePlanExecutor()
        executor._conversation = mock_conversation  # type: ignore[attr-defined]

        # Execute
        action = ExecutePlanAction(plan_file="PLAN.md")

        with patch("openhands.sdk.agent.registry.AgentRegistry") as mock_registry:
            mock_registry.create.return_value = Mock()
            result = executor(action)

        # Verify
        assert result.success is True
        assert result.plan_content == plan_content
