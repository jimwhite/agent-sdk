"""Tests for child conversation functionality."""

import os
import tempfile
import uuid
from unittest.mock import Mock

import pytest

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.conversation.registry import get_conversation_registry
from openhands.sdk.llm import LLM


class TestAgent(AgentBase):
    """Test agent for testing."""

    def __init__(self, llm: LLM):
        super().__init__(llm=llm, tools=[])

    def step(self, state, on_event=None):
        """Mock step implementation."""
        pass


class ChildAgent(AgentBase):
    """Child agent for testing."""

    def __init__(self, llm: LLM):
        super().__init__(llm=llm, tools=[])

    def step(self, state, on_event=None):
        """Mock step implementation."""
        pass


class TestExecutionAgent(AgentBase):
    """Test execution agent for testing."""

    def __init__(self, llm: LLM):
        super().__init__(llm=llm, tools=[])

    def step(self, state, on_event=None):
        """Mock step implementation."""
        pass


class TestPlanningAgent(AgentBase):
    """Test planning agent for testing."""

    def __init__(self, llm: LLM):
        super().__init__(llm=llm, tools=[])

    def step(self, state, on_event=None):
        """Mock step implementation."""
        pass


@pytest.fixture
def test_llm():
    """Create a test LLM for testing."""
    from pydantic import SecretStr

    from openhands.sdk.llm.llm import LLM

    return LLM(
        model="mock-model", api_key=SecretStr("mock-key"), service_id="test-service"
    )


@pytest.fixture
def test_agent(test_llm):
    """Create a test agent for testing."""
    return TestAgent(test_llm)


@pytest.fixture
def child_agent(test_llm):
    """Create a child agent for testing."""
    return ChildAgent(test_llm)


@pytest.fixture
def execution_agent(test_llm):
    """Create an execution agent for testing."""
    return TestExecutionAgent(test_llm)


@pytest.fixture
def planning_agent(test_llm):
    """Create a planning agent for testing."""
    return TestPlanningAgent(test_llm)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


def test_conversation_state_parent_id(test_agent, temp_dir):
    """Test that ConversationState can be created (parent_id handled by registry)."""
    from openhands.sdk.conversation.state import ConversationState
    from openhands.sdk.workspace import LocalWorkspace

    state = ConversationState.create(
        id=uuid.uuid4(),
        agent=test_agent,
        workspace=LocalWorkspace(working_dir=temp_dir),
    )

    # Parent-child relationships are now managed by the registry, not the state
    assert hasattr(state, "id")


def test_conversation_state_no_parent_id(test_agent, temp_dir):
    """Test that ConversationState works (parent_id is now handled by registry)."""
    from openhands.sdk.conversation.state import ConversationState
    from openhands.sdk.workspace import LocalWorkspace

    state = ConversationState.create(
        id=uuid.uuid4(),
        agent=test_agent,
        workspace=LocalWorkspace(working_dir=temp_dir),
    )

    # Parent-child relationships are now managed by the registry, not the state
    assert hasattr(state, "id")


def test_local_conversation_child_tracking_initialization(test_agent, temp_dir):
    """Test that LocalConversation initializes without local child tracking."""
    conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    # Verify that local child tracking is not present (delegated to registry)
    assert not hasattr(conversation, "_child_conversations")
    # Verify that child conversation methods are not present (delegated to registry)
    assert not hasattr(conversation, "list_child_conversations")
    assert not hasattr(conversation, "create_child_conversation")
    assert not hasattr(conversation, "get_child_conversation")


def test_create_child_conversation(test_agent, child_agent, temp_dir):
    """Test creating a child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()
    child_conversation = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )

    # Check child conversation properties
    assert child_conversation is not None
    assert isinstance(child_conversation, LocalConversation)
    assert child_conversation.agent is child_agent
    # Parent-child relationship is now managed by the registry

    # Check parent tracking via registry
    child_id = child_conversation._state.id
    assert child_id in registry.list_child_conversations(parent_conversation._state.id)
    assert (
        registry.get_child_conversation(parent_conversation._state.id, child_id)
        is child_conversation
    )

    # Check working directory structure (new pattern: parent-uuid/child-uuid)
    parent_id = parent_conversation._state.id
    expected_path = os.path.join(
        temp_dir, ".conversations", str(parent_id), str(child_id)
    )
    assert child_conversation._state.workspace.working_dir == expected_path
    assert os.path.exists(expected_path)

    # Check children.json mapping exists
    children_file = os.path.join(
        temp_dir, ".conversations", str(parent_id), "children.json"
    )
    assert os.path.exists(children_file)

    # Check children.json content
    import json

    with open(children_file) as f:
        children_mapping = json.load(f)

    assert str(child_id) in children_mapping
    assert children_mapping[str(child_id)]["agent_type"] == "child"
    assert children_mapping[str(child_id)]["agent_class"] == "ChildAgent"


def test_create_child_conversation_custom_working_dir(
    test_agent, child_agent, temp_dir
):
    """Test creating a child conversation with custom working directory."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    custom_dir = os.path.join(temp_dir, "custom_child_dir")

    registry = get_conversation_registry()
    child_conversation = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        working_dir=custom_dir,
        visualize=False,
    )

    assert isinstance(child_conversation, LocalConversation)
    assert child_conversation._state.workspace.working_dir == custom_dir


def test_get_child_conversation(test_agent, child_agent, temp_dir):
    """Test retrieving a child conversation by ID."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()
    child_conversation = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )

    assert isinstance(child_conversation, LocalConversation)
    child_id = child_conversation._state.id
    retrieved_child = registry.get_child_conversation(
        parent_conversation._state.id, child_id
    )

    assert retrieved_child is child_conversation


def test_get_nonexistent_child_conversation(test_agent, temp_dir):
    """Test retrieving a non-existent child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()
    nonexistent_id = uuid.uuid4()
    retrieved_child = registry.get_child_conversation(
        parent_conversation._state.id, nonexistent_id
    )

    assert retrieved_child is None


def test_close_child_conversation(test_agent, child_agent, temp_dir):
    """Test closing a child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()
    child_conversation = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )

    assert isinstance(child_conversation, LocalConversation)
    child_id = child_conversation._state.id

    # Verify child exists in children.json before closing
    children_mapping = registry.get_children_mapping(parent_conversation._state.id)
    assert str(child_id) in children_mapping

    # Mock the close method to track if it was called
    child_conversation.close = Mock()

    registry.close_child_conversation(parent_conversation._state.id, child_id)

    # Check that child was closed and removed
    child_conversation.close.assert_called_once()
    assert child_id not in registry.list_child_conversations(
        parent_conversation._state.id
    )

    # Check that child was removed from children.json
    children_mapping = registry.get_children_mapping(parent_conversation._state.id)
    assert str(child_id) not in children_mapping


def test_close_nonexistent_child_conversation(test_agent, temp_dir):
    """Test closing a non-existent child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()
    nonexistent_id = uuid.uuid4()

    # Should not raise an exception
    registry.close_child_conversation(parent_conversation._state.id, nonexistent_id)


def test_list_child_conversations(test_agent, child_agent, temp_dir):
    """Test listing child conversation IDs."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()

    # Initially no children
    assert registry.list_child_conversations(parent_conversation._state.id) == []

    # Create multiple children
    child1 = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )
    child2 = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )

    assert isinstance(child1, LocalConversation)
    assert isinstance(child2, LocalConversation)
    child_ids = registry.list_child_conversations(parent_conversation._state.id)
    assert len(child_ids) == 2
    assert child1._state.id in child_ids
    assert child2._state.id in child_ids


def test_parent_conversation_close_closes_children(test_agent, child_agent, temp_dir):
    """Test that closing parent conversation closes all children."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()

    # Create child conversations
    child1 = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )
    child2 = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )

    assert isinstance(child1, LocalConversation)
    assert isinstance(child2, LocalConversation)

    # Mock close methods
    child1.close = Mock()
    child2.close = Mock()

    # Close parent
    parent_conversation.close()

    # Check that children were closed
    child1.close.assert_called_once()
    child2.close.assert_called_once()

    # Check that children were removed from tracking
    assert len(registry.list_child_conversations(parent_conversation._state.id)) == 0


def test_agent_type_directory_naming(
    test_agent, execution_agent, planning_agent, temp_dir
):
    """Test that agent type is correctly stored in children.json mapping."""
    # Test different agent types and their expected types in mapping
    test_cases = [
        (execution_agent, "testexecution"),
        (planning_agent, "testplanning"),
    ]

    for agent, expected_type in test_cases:
        parent_conversation = LocalConversation(
            agent=test_agent,
            workspace=temp_dir,
            visualize=False,
        )

        registry = get_conversation_registry()
        child_conversation = registry.create_child_conversation(
            parent_id=parent_conversation._state.id,
            agent=agent,
            visualize=False,
        )

        assert isinstance(child_conversation, LocalConversation)
        child_id = child_conversation._state.id
        parent_id = parent_conversation._state.id

        # Check new directory structure: parent-uuid/child-uuid
        expected_path = os.path.join(
            temp_dir, ".conversations", str(parent_id), str(child_id)
        )
        assert child_conversation._state.workspace.working_dir == expected_path

        # Check children.json mapping contains correct agent type
        children_mapping = registry.get_children_mapping(parent_conversation._state.id)
        assert str(child_id) in children_mapping
        assert children_mapping[str(child_id)]["agent_type"] == expected_type

        # Clean up for next iteration
        parent_conversation.close()


def test_multiple_child_conversations_parallel(
    test_agent, execution_agent, planning_agent, temp_dir
):
    """Test that multiple child conversations can exist simultaneously."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()

    # Create children
    execution_child = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=execution_agent,
        visualize=False,
    )
    planning_child = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=planning_agent,
        visualize=False,
    )

    assert isinstance(execution_child, LocalConversation)
    assert isinstance(planning_child, LocalConversation)

    # Both should exist simultaneously
    assert len(registry.list_child_conversations(parent_conversation._state.id)) == 2

    # Should be in different directories under parent UUID
    execution_path = execution_child._state.workspace.working_dir
    planning_path = planning_child._state.workspace.working_dir
    parent_id = parent_conversation._state.id

    assert str(parent_id) in execution_path
    assert str(parent_id) in planning_path
    assert execution_path != planning_path

    # Both should be retrievable
    assert (
        registry.get_child_conversation(
            parent_conversation._state.id, execution_child._state.id
        )
        is execution_child
    )
    assert (
        registry.get_child_conversation(
            parent_conversation._state.id, planning_child._state.id
        )
        is planning_child
    )

    # Both should be in children.json mapping
    children_mapping = registry.get_children_mapping(parent_conversation._state.id)
    assert str(execution_child._state.id) in children_mapping
    assert str(planning_child._state.id) in children_mapping
    assert (
        children_mapping[str(execution_child._state.id)]["agent_type"]
        == "testexecution"
    )
    assert (
        children_mapping[str(planning_child._state.id)]["agent_type"] == "testplanning"
    )


def test_get_children_mapping(test_agent, child_agent, temp_dir):
    """Test getting children mapping from children.json."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        workspace=temp_dir,
        visualize=False,
    )

    registry = get_conversation_registry()

    # Initially no children
    children_mapping = registry.get_children_mapping(parent_conversation._state.id)
    assert children_mapping == {}

    # Create a child
    child_conversation = registry.create_child_conversation(
        parent_id=parent_conversation._state.id,
        agent=child_agent,
        visualize=False,
    )
    assert isinstance(child_conversation, LocalConversation)
    child_id = child_conversation._state.id

    # Check mapping contains the child
    children_mapping = registry.get_children_mapping(parent_conversation._state.id)
    assert str(child_id) in children_mapping
    assert children_mapping[str(child_id)]["agent_type"] == "child"
    assert children_mapping[str(child_id)]["agent_class"] == "ChildAgent"
    assert "created_at" in children_mapping[str(child_id)]

    # Clean up
    parent_conversation.close()
