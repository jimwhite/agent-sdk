"""Tests for AgentDispatcher with new architecture."""

import uuid
from unittest.mock import Mock, patch

from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.llm.message import TextContent
from openhands.sdk.tool.tools.agent_dispatcher import (
    AgentDispatcher,
    SpawnChildObservation,
    SpawnExecutionChildAction,
    SpawnExecutionChildExecutor,
    SpawnPlanningChildAction,
    SpawnPlanningChildExecutor,
)


class TestAgentDispatcher:
    """Test cases for AgentDispatcher."""

    @patch("openhands.sdk.tool.tools.agent_dispatcher.AgentRegistry")
    def test_init(self, mock_agent_registry):
        """Test AgentDispatcher initialization."""
        mock_registry_instance = Mock()
        mock_registry_instance.list_agents.return_value = {
            "planning": "Planning agent description",
            "execution": "Execution agent description",
        }
        mock_agent_registry.return_value = mock_registry_instance

        dispatcher = AgentDispatcher()

        assert dispatcher._agent_registry == mock_registry_instance
        assert dispatcher._available_agents == {
            "planning": "Planning agent description",
            "execution": "Execution agent description",
        }
        mock_registry_instance.list_agents.assert_called_once()

    @patch("openhands.sdk.tool.tools.agent_dispatcher.AgentRegistry")
    def test_create_planning_tool_success(self, mock_agent_registry):
        """Test successful planning tool creation."""
        mock_registry_instance = Mock()
        mock_registry_instance.list_agents.return_value = {
            "planning": "Planning agent description",
        }
        mock_agent_registry.return_value = mock_registry_instance

        mock_conv_state = Mock()
        mock_conv_state.id = ConversationID(str(uuid.uuid4()))

        dispatcher = AgentDispatcher()
        tool = dispatcher.create_planning_tool(mock_conv_state)

        assert tool.name == "spawn_planning_child"
        assert "Planning agent description" in tool.description
        assert tool.action_type == SpawnPlanningChildAction
        assert tool.observation_type == SpawnChildObservation

    @patch("openhands.sdk.tool.tools.agent_dispatcher.AgentRegistry")
    def test_create_execution_tool_success(self, mock_agent_registry):
        """Test successful execution tool creation."""
        mock_registry_instance = Mock()
        mock_registry_instance.list_agents.return_value = {
            "execution": "Execution agent description",
        }
        mock_agent_registry.return_value = mock_registry_instance

        mock_conv_state = Mock()
        mock_conv_state.id = ConversationID(str(uuid.uuid4()))

        dispatcher = AgentDispatcher()
        tool = dispatcher.create_execution_tool(mock_conv_state)

        assert tool.name == "spawn_execution_child"
        assert "Execution agent description" in tool.description
        assert tool.action_type == SpawnExecutionChildAction
        assert tool.observation_type == SpawnChildObservation

    @patch("openhands.sdk.tool.tools.agent_dispatcher.AgentRegistry")
    def test_generate_tool_description(self, mock_agent_registry):
        """Test tool description generation."""
        mock_registry_instance = Mock()
        mock_registry_instance.list_agents.return_value = {
            "planning": "Creates detailed plans",
        }
        mock_agent_registry.return_value = mock_registry_instance

        dispatcher = AgentDispatcher()
        description = dispatcher._generate_tool_description("planning")

        assert "Creates detailed plans" in description


class TestSpawnPlanningChildExecutor:
    """Test cases for SpawnPlanningChildExecutor."""

    def test_init(self):
        """Test executor initialization."""
        conv_id = ConversationID(str(uuid.uuid4()))
        executor = SpawnPlanningChildExecutor(conv_id)
        assert executor._conversation_id == conv_id
        assert executor._agent_type == "planning"

    def test_call_no_conversation_id(self):
        """Test executor call with no conversation ID."""
        executor = SpawnPlanningChildExecutor(None)
        action = SpawnPlanningChildAction(task_description="Test task")

        observation = executor(action)

        assert isinstance(observation, SpawnChildObservation)
        assert not observation.success
        assert "No conversation ID available" in observation.error_message

    @patch("openhands.sdk.tool.tools.agent_dispatcher.ConversationManager")
    def test_call_conversation_not_found(self, mock_conv_manager):
        """Test executor call when conversation is not found."""
        conv_id = ConversationID(str(uuid.uuid4()))
        mock_manager_instance = Mock()
        mock_manager_instance.get_conversation.return_value = None
        mock_conv_manager.return_value = mock_manager_instance

        executor = SpawnPlanningChildExecutor(conv_id)
        action = SpawnPlanningChildAction(task_description="Test task")

        observation = executor(action)

        assert isinstance(observation, SpawnChildObservation)
        assert not observation.success
        assert "Conversation not found" in observation.error_message

    @patch("openhands.sdk.tool.tools.agent_dispatcher.ConversationManager")
    @patch("openhands.sdk.tool.tools.agent_dispatcher.AgentRegistry")
    def test_call_success(self, mock_agent_registry, mock_conv_manager):
        """Test successful executor call."""
        conv_id = ConversationID(str(uuid.uuid4()))
        child_conv_id = ConversationID(str(uuid.uuid4()))

        # Mock conversation manager
        mock_manager_instance = Mock()
        mock_conversation = Mock()
        mock_conversation.id = conv_id
        mock_manager_instance.get_conversation.return_value = mock_conversation
        mock_manager_instance.create_conversation.return_value = child_conv_id
        mock_conv_manager.return_value = mock_manager_instance

        # Mock agent registry
        mock_registry_instance = Mock()
        mock_agent_registry.return_value = mock_registry_instance

        executor = SpawnPlanningChildExecutor(conv_id)
        action = SpawnPlanningChildAction(task_description="Test task")

        observation = executor(action)

        assert isinstance(observation, SpawnChildObservation)
        assert observation.success
        assert observation.child_conversation_id == child_conv_id
        assert observation.agent_type == "planning"
        mock_manager_instance.create_conversation.assert_called_once_with(
            parent_conversation_id=conv_id
        )


class TestSpawnExecutionChildExecutor:
    """Test cases for SpawnExecutionChildExecutor."""

    def test_init(self):
        """Test executor initialization."""
        conv_id = ConversationID(str(uuid.uuid4()))
        executor = SpawnExecutionChildExecutor(conv_id)
        assert executor._conversation_id == conv_id
        assert executor._agent_type == "execution"


class TestSpawnPlanningChildAction:
    """Test cases for SpawnPlanningChildAction."""

    def test_visualize(self):
        """Test action visualization."""
        action = SpawnPlanningChildAction(
            task_description="Create a plan for the project"
        )

        content = action.to_llm_content

        assert len(content) == 1
        assert isinstance(content[0], TextContent)
        assert "Spawning planning child with task:" in str(content[0].text)
        assert "Create a plan for the project" in str(content[0].text)

    def test_visualize_long_description(self):
        """Test action visualization with long description."""
        long_description = "A" * 150
        action = SpawnPlanningChildAction(task_description=long_description)

        content = action.to_llm_content

        assert len(content) == 1
        assert isinstance(content[0], TextContent)
        text_content = str(content[0].text)
        assert "Spawning planning child with task:" in text_content
        assert "..." in text_content
        assert len(text_content) < len(long_description) + 50


class TestSpawnExecutionChildAction:
    """Test cases for SpawnExecutionChildAction."""

    def test_visualize(self):
        """Test action visualization."""
        action = SpawnExecutionChildAction(task_description="Execute the plan")

        content = action.to_llm_content

        assert len(content) == 1
        assert isinstance(content[0], TextContent)
        assert "Spawning execution child with task:" in str(content[0].text)
        assert "Execute the plan" in str(content[0].text)


class TestSpawnChildObservation:
    """Test cases for SpawnChildObservation."""

    def test_agent_observation_success(self):
        """Test successful agent observation."""
        child_conv_id = ConversationID(str(uuid.uuid4()))
        observation = SpawnChildObservation.agent_observation(
            child_conversation_id=child_conv_id,
            agent_type="planning",
            task_description="Test task",
        )

        assert observation.success
        assert observation.child_conversation_id == child_conv_id
        assert observation.agent_type == "planning"
        assert observation.task_description == "Test task"
        assert observation.error_message is None

    def test_agent_observation_failure(self):
        """Test failed agent observation."""
        observation = SpawnChildObservation.agent_observation_failure(
            "Test error message"
        )

        assert not observation.success
        assert observation.child_conversation_id is None
        assert observation.agent_type is None
        assert observation.task_description is None
        assert observation.error_message == "Test error message"

    def test_visualize_success(self):
        """Test visualization of successful observation."""
        child_conv_id = ConversationID(str(uuid.uuid4()))
        observation = SpawnChildObservation.agent_observation(
            child_conversation_id=child_conv_id,
            agent_type="planning",
            task_description="Test task",
        )

        content = observation.to_llm_content

        assert len(content) == 1
        assert isinstance(content[0], TextContent)
        text_content = str(content[0].text)
        assert "Successfully spawned planning child agent" in text_content
        assert str(child_conv_id) in text_content

    def test_visualize_failure(self):
        """Test visualization of failed observation."""
        observation = SpawnChildObservation.agent_observation_failure(
            "Test error message"
        )

        content = observation.to_llm_content

        assert len(content) == 1
        assert isinstance(content[0], TextContent)
        text_content = str(content[0].text)
        assert "Failed to spawn child agent" in text_content
        assert "Test error message" in text_content
