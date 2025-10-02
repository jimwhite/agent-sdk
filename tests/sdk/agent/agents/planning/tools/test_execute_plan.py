"""Tests for execute_plan tool."""

import os
import tempfile
from unittest.mock import Mock, mock_open, patch

from openhands.sdk.agent.agents.planning.tools.execute_plan import (
    ExecutePlanAction,
    ExecutePlanExecutor,
    ExecutePlanObservation,
    ExecutePlanTool,
)
from openhands.sdk.llm.message import TextContent


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
    agent_obs = obs.to_llm_content
    assert len(agent_obs) == 1
    assert isinstance(agent_obs[0], TextContent)
    assert "SUCCESS:" in agent_obs[0].text
    assert "exec-123" in agent_obs[0].text

    # Test visualization
    viz = obs.visualize
    assert "SUCCESS:" in str(viz)


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
    agent_obs = obs.to_llm_content
    assert len(agent_obs) == 1
    assert isinstance(agent_obs[0], TextContent)
    assert "ERROR:" in agent_obs[0].text
    assert "Plan file not found" in agent_obs[0].text

    # Test visualization
    viz = obs.visualize
    assert "ERROR:" in str(viz)


def test_execute_plan_executor_no_conversation():
    """Test executor when no conversation is available."""
    executor = ExecutePlanExecutor()
    action = ExecutePlanAction(plan_file="PLAN.md")

    result = executor(action)

    assert result.success is False
    assert result.error is not None
    assert "No conversation ID provided" in result.error


def test_execute_plan_executor_file_not_found():
    """Test executor when plan file doesn't exist."""
    from uuid import uuid4

    conversation_id = str(uuid4())
    mock_conversation = Mock()
    mock_conversation._state.workspace.working_dir = "/tmp/test"

    executor = ExecutePlanExecutor(conversation_id)

    action = ExecutePlanAction(plan_file="PLAN.md")

    with patch(
        "openhands.sdk.conversation.registry.get_conversation_registry"
    ) as mock_registry:
        mock_registry.return_value.get.return_value = mock_conversation
        with patch("os.path.exists", return_value=False):
            result = executor(action)

    assert result.success is False
    assert result.error is not None
    assert "Plan file PLAN.md not found" in result.error


def test_execute_plan_executor_empty_file():
    """Test executor when plan file is empty."""
    from uuid import uuid4

    conversation_id = str(uuid4())
    mock_conversation = Mock()
    mock_conversation._state.workspace.working_dir = "/tmp/test"

    executor = ExecutePlanExecutor(conversation_id)

    action = ExecutePlanAction(plan_file="PLAN.md")

    with patch(
        "openhands.sdk.conversation.registry.get_conversation_registry"
    ) as mock_registry:
        mock_registry.return_value.get.return_value = mock_conversation
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data="")),
        ):
            result = executor(action)

    assert result.success is False
    assert result.error is not None
    assert "Plan file PLAN.md is empty" in result.error


def test_execute_plan_executor_success():
    """Test successful execution of execute_plan."""
    from uuid import uuid4

    conversation_id = str(uuid4())
    mock_conversation = Mock()
    mock_conversation._state.workspace.working_dir = "/tmp/test"

    mock_parent_conversation = Mock()

    # Create executor
    executor = ExecutePlanExecutor(conversation_id)

    # Execute
    action = ExecutePlanAction(plan_file="PLAN.md")
    plan_content = "# Plan\n1. Step one\n2. Step two"

    with patch(
        "openhands.sdk.conversation.registry.get_conversation_registry"
    ) as mock_registry:
        mock_registry.return_value.get.return_value = mock_conversation
        mock_registry.return_value.get_parent_conversation.return_value = (
            mock_parent_conversation
        )
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=plan_content)),
        ):
            result = executor(action)

    # Verify
    assert result.success is True
    assert result.child_conversation_id is None  # No child created
    assert result.working_directory == "/tmp/test/PLAN.md"
    assert "Plan sent back to parent conversation" in result.message
    assert result.plan_content == plan_content

    # Verify calls
    mock_parent_conversation.send_message.assert_called_once()
    mock_parent_conversation.run.assert_called_once()
    mock_conversation.close.assert_called_once()


def test_execute_plan_executor_failure():
    """Test executor failure handling."""
    from uuid import uuid4

    conversation_id = str(uuid4())
    mock_conversation = Mock()
    mock_conversation._state.workspace.working_dir = "/tmp/test"

    # Create executor
    executor = ExecutePlanExecutor(conversation_id)

    # Execute
    action = ExecutePlanAction(plan_file="PLAN.md")
    plan_content = "# Plan\n1. Step one"

    with patch(
        "openhands.sdk.conversation.registry.get_conversation_registry"
    ) as mock_registry:
        mock_registry.return_value.get.return_value = mock_conversation
        # Mock get_parent_conversation to return None (no parent)
        mock_registry.return_value.get_parent_conversation.return_value = None
        with (
            patch("os.path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=plan_content)),
        ):
            result = executor(action)

    # Verify
    assert result.success is False
    assert result.error is not None
    assert "No parent conversation found" in result.error


def test_execute_plan_tool_structure():
    """Test the tool structure and properties."""
    from unittest.mock import Mock
    from uuid import uuid4

    from openhands.sdk.conversation.state import ConversationState

    # Create a mock conversation state
    mock_conv_state = Mock(spec=ConversationState)
    mock_conv_state.id = uuid4()

    tools = ExecutePlanTool.create(mock_conv_state)
    assert len(tools) == 1

    tool = tools[0]
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
    from uuid import uuid4

    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a real plan file
        plan_file = os.path.join(temp_dir, "PLAN.md")
        plan_content = "# Test Plan\n1. First step\n2. Second step"

        with open(plan_file, "w") as f:
            f.write(plan_content)

        # Setup mocks
        conversation_id = str(uuid4())
        mock_conversation = Mock()
        mock_conversation._state.workspace.working_dir = temp_dir
        mock_conversation._agent.llm = Mock()

        mock_child_conversation = Mock()
        mock_child_conversation._state.id = "exec-456"
        mock_child_conversation._state.workspace.working_dir = "/tmp/exec"
        mock_conversation.create_child_conversation.return_value = (
            mock_child_conversation
        )

        # Create executor
        executor = ExecutePlanExecutor(conversation_id)

        # Execute
        action = ExecutePlanAction(plan_file="PLAN.md")

        with patch(
            "openhands.sdk.conversation.registry.get_conversation_registry"
        ) as mock_registry:
            mock_registry.return_value.get.return_value = mock_conversation
            mock_registry.return_value.get_parent_conversation.return_value = Mock()
            with patch(
                "openhands.sdk.agent.registry.AgentRegistry"
            ) as mock_agent_registry:
                mock_agent_registry.create.return_value = Mock()
                result = executor(action)

        # Verify
        assert result.success is True
        assert result.plan_content == plan_content
