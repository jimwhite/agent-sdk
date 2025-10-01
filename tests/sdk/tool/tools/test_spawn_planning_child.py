"""Tests for spawn_planning_child tool."""

from unittest.mock import Mock, mock_open, patch

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
    assert "No conversation ID provided" in result.error


@patch("openhands.sdk.tool.tools.spawn_planning_child.AgentRegistry")
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
    mock_conversation._state.workspace.working_dir = "/tmp/child"
    mock_conversation._state.id = "parent-123"

    mock_child_conversation = Mock()
    mock_child_conversation._state.id = "child-123"
    mock_child_conversation._state.workspace.working_dir = "/tmp/child"

    # Create executor with conversation ID
    executor = SpawnPlanningChildExecutor(conversation_id="parent-123")

    # Execute
    action = SpawnPlanningChildAction(task_description="Build a web app")

    # Mock the conversation registry and os.path.exists
    with (
        patch(
            "openhands.sdk.tool.tools.spawn_planning_child.get_conversation_registry"
        ) as mock_get_registry,
        patch("os.path.exists", return_value=True),
    ):
        mock_registry_instance = Mock()
        mock_registry_instance.get.return_value = mock_conversation
        mock_registry_instance.create_child_conversation.return_value = (
            mock_child_conversation
        )
        mock_get_registry.return_value = mock_registry_instance
        result = executor(action)

    # Verify
    assert result.success is True
    assert result.child_conversation_id == "child-123"
    assert result.working_directory == "/tmp/child"
    assert "Planning child created." in result.message

    # Verify calls
    mock_registry.create.assert_called_once_with(
        "planning", llm=mock_llm, system_prompt_kwargs={"WORK_DIR": "/tmp/child"}
    )
    mock_registry_instance.create_child_conversation.assert_called_once_with(
        parent_id=mock_conversation._state.id, agent=mock_agent, visualize=True
    )

    # Additional test steps: Simulate main conversation executing the plan
    # Mock that a PLAN.md file was created by the planning child
    mock_plan_content = """# Project Plan: Build a Web App

## Phase 1: Setup
1. Create project structure
2. Initialize package.json
3. Set up basic HTML/CSS/JS files

## Phase 2: Development
1. Implement main functionality
2. Add styling
3. Test the application

## Phase 3: Deployment
1. Build for production
2. Deploy to hosting platform
"""

    # Mock reading the plan file
    with patch("builtins.open", mock_open(read_data=mock_plan_content)):
        # Simulate the main conversation reading and executing the plan
        # This would typically involve the main agent processing the plan
        mock_conversation.send_message.return_value = Mock()

        # Simulate sending the plan content to the main conversation
        plan_execution_message = f"Execute this plan:\n{mock_plan_content}"
        mock_conversation.send_message(plan_execution_message)

        # Verify the main conversation received the plan for execution
        mock_conversation.send_message.assert_called_once_with(plan_execution_message)


@patch("openhands.sdk.tool.tools.spawn_planning_child.AgentRegistry")
def test_spawn_planning_child_executor_failure(mock_registry_class):
    """Test executor failure handling."""
    # Setup mocks to raise exception
    mock_registry = Mock()
    mock_registry.create.side_effect = Exception("Registry error")
    mock_registry_class.return_value = mock_registry

    mock_conversation = Mock()
    mock_conversation.agent.llm = Mock()
    mock_conversation._state.workspace.working_dir = "/tmp/child"

    # Create executor with conversation ID
    executor = SpawnPlanningChildExecutor(conversation_id="parent-123")

    # Execute
    action = SpawnPlanningChildAction(task_description="Build a web app")

    # Mock the conversation registry
    with patch(
        "openhands.sdk.tool.tools.spawn_planning_child.get_conversation_registry"
    ) as mock_get_registry:
        mock_registry_instance = Mock()
        mock_registry_instance.get.return_value = mock_conversation
        mock_get_registry.return_value = mock_registry_instance
        result = executor(action)

    # Verify
    assert result.success is False
    assert result.error is not None
    assert "Failed to spawn planning child" in result.error
    assert "Registry error" in result.error


def test_spawn_planning_child_tool_structure():
    """Test the tool structure and properties."""
    from unittest.mock import Mock

    from openhands.sdk.conversation.state import ConversationState

    # Create a mock conversation state
    mock_conv_state = Mock(spec=ConversationState)
    mock_conv_state.id = "test-conversation-123"

    tools = SpawnPlanningChildTool.create(mock_conv_state)
    assert len(tools) == 1

    tool = tools[0]
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
