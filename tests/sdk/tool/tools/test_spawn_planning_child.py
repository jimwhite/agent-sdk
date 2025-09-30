"""Tests for spawn_planning_child tool."""

from unittest.mock import Mock, patch

from openhands.sdk.llm.message import TextContent
from openhands.sdk.tool.tools.spawn_planning_child import (
    SpawnPlanningChildAction,
    SpawnPlanningChildExecutor,
    SpawnPlanningChildObservation,
    SpawnPlanningChildTool,
)


def test_spawn_planning_child_action():
    """Test SpawnPlanningChildAction creation and properties."""
    action = SpawnPlanningChildAction(task_description="Build a web app")

    assert action.task_description == "Build a web app"

    # Test visualization
    viz = action.visualize
    assert "Spawning Planning Child" in str(viz)
    assert "Build a web app" in str(viz)


def test_spawn_planning_child_observation_success():
    """Test successful SpawnPlanningChildObservation."""
    obs = SpawnPlanningChildObservation(
        success=True,
        child_conversation_id="child-123",
        message="Created planning child",
        working_directory="/tmp/child",
    )

    assert obs.success is True
    assert obs.child_conversation_id == "child-123"
    assert obs.message == "Created planning child"
    assert obs.working_directory == "/tmp/child"
    assert obs.error is None

    # Test agent observation
    agent_obs = obs.agent_observation
    assert len(agent_obs) == 1
    assert isinstance(agent_obs[0], TextContent)
    assert "✅" in agent_obs[0].text
    assert "child-123" in agent_obs[0].text

    # Test visualization
    viz = obs.visualize
    assert "✅" in str(viz)


def test_spawn_planning_child_observation_failure():
    """Test failed SpawnPlanningChildObservation."""
    obs = SpawnPlanningChildObservation(
        success=False,
        message="",
        error="Failed to create child",
    )

    assert obs.success is False
    assert obs.error == "Failed to create child"

    # Test agent observation
    agent_obs = obs.agent_observation
    assert len(agent_obs) == 1
    assert isinstance(agent_obs[0], TextContent)
    assert "❌" in agent_obs[0].text
    assert "Failed to create child" in agent_obs[0].text

    # Test visualization
    viz = obs.visualize
    assert "❌" in str(viz)


def test_spawn_planning_child_executor_no_conversation():
    """Test executor when no conversation is available."""
    executor = SpawnPlanningChildExecutor()
    action = SpawnPlanningChildAction(task_description="Test task")

    result = executor(action)

    assert result.success is False
    assert result.error is not None
    assert "No active conversation found" in result.error


@patch("openhands.sdk.agent.registry.AgentRegistry")
def test_spawn_planning_child_executor_success(mock_registry_class):
    """Test successful execution of spawn_planning_child."""
    # Setup mocks
    mock_llm = Mock()
    mock_agent = Mock()

    # Mock the registry instance
    mock_registry = Mock()
    mock_registry.create.return_value = mock_agent
    mock_registry_class.return_value = mock_registry

    mock_conversation = Mock()
    mock_conversation.agent.llm = mock_llm

    mock_child_conversation = Mock()
    mock_child_conversation._state.id = "child-123"
    mock_child_conversation._state.working_dir = "/tmp/child"
    mock_conversation.create_child_conversation.return_value = mock_child_conversation

    # Create executor and set conversation
    executor = SpawnPlanningChildExecutor()
    executor._conversation = mock_conversation  # type: ignore[attr-defined]

    # Execute
    action = SpawnPlanningChildAction(task_description="Build a web app")
    result = executor(action)

    # Verify
    assert result.success is True
    assert result.child_conversation_id == "child-123"
    assert result.working_directory == "/tmp/child"
    assert "Created planning child conversation" in result.message

    # Verify calls
    mock_registry.create.assert_called_once_with("planning", llm=mock_llm)
    mock_conversation.create_child_conversation.assert_called_once_with(
        agent=mock_agent, visualize=False
    )
    mock_child_conversation.send_message.assert_called_once()


@patch("openhands.sdk.agent.registry.AgentRegistry")
def test_spawn_planning_child_executor_failure(mock_registry_class):
    """Test executor failure handling."""
    # Setup mocks to raise exception
    mock_registry = Mock()
    mock_registry.create.side_effect = Exception("Registry error")
    mock_registry_class.return_value = mock_registry

    mock_conversation = Mock()
    mock_conversation.agent.llm = Mock()

    # Create executor and set conversation
    executor = SpawnPlanningChildExecutor()
    executor._conversation = mock_conversation  # type: ignore[attr-defined]

    # Execute
    action = SpawnPlanningChildAction(task_description="Build a web app")
    result = executor(action)

    # Verify
    assert result.success is False
    assert result.error is not None
    assert "Failed to spawn planning child conversation" in result.error
    assert "Registry error" in result.error


def test_spawn_planning_child_tool_structure():
    """Test the tool structure and properties."""
    tool = SpawnPlanningChildTool

    assert tool.name == "spawn_planning_child"
    assert "spawn a child conversation" in tool.description.lower()
    assert tool.action_type == SpawnPlanningChildAction
    assert tool.observation_type == SpawnPlanningChildObservation
    assert isinstance(tool.executor, SpawnPlanningChildExecutor)

    # Test annotations
    assert tool.annotations is not None
    assert tool.annotations.readOnlyHint is False
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is False
    assert tool.annotations.openWorldHint is True
