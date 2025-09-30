"""Tests for child conversation functionality."""

import os
import tempfile
import uuid
from unittest.mock import Mock

import pytest

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
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
    """Test that ConversationState supports parent_id."""
    from openhands.sdk.conversation.state import ConversationState

    parent_id = uuid.uuid4()

    state = ConversationState.create(
        id=uuid.uuid4(),
        agent=test_agent,
        working_dir=temp_dir,
        parent_id=parent_id,
    )

    assert state.parent_id == parent_id


def test_conversation_state_no_parent_id(test_agent, temp_dir):
    """Test that ConversationState works without parent_id."""
    from openhands.sdk.conversation.state import ConversationState

    state = ConversationState.create(
        id=uuid.uuid4(),
        agent=test_agent,
        working_dir=temp_dir,
    )

    assert state.parent_id is None


def test_local_conversation_child_tracking_initialization(test_agent, temp_dir):
    """Test that LocalConversation initializes child conversation tracking."""
    conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    assert hasattr(conversation, "_child_conversations")
    assert isinstance(conversation._child_conversations, dict)
    assert len(conversation._child_conversations) == 0


def test_create_child_conversation(test_agent, child_agent, temp_dir):
    """Test creating a child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    child_conversation = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )

    # Check child conversation properties
    assert child_conversation is not None
    assert child_conversation.agent is child_agent
    assert child_conversation._state.parent_id == parent_conversation._state.id

    # Check parent tracking
    child_id = child_conversation._state.id
    assert child_id in parent_conversation._child_conversations
    assert parent_conversation._child_conversations[child_id] is child_conversation

    # Check working directory structure (new pattern: parent-uuid/child-uuid)
    parent_id = parent_conversation._state.id
    expected_path = os.path.join(
        temp_dir, ".conversations", str(parent_id), str(child_id)
    )
    assert child_conversation._state.working_dir == expected_path
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
        working_dir=temp_dir,
        visualize=False,
    )

    custom_dir = os.path.join(temp_dir, "custom_child_dir")

    child_conversation = parent_conversation.create_child_conversation(
        agent=child_agent,
        working_dir=custom_dir,
        visualize=False,
    )

    assert child_conversation._state.working_dir == custom_dir


def test_get_child_conversation(test_agent, child_agent, temp_dir):
    """Test retrieving a child conversation by ID."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    child_conversation = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )

    child_id = child_conversation._state.id
    retrieved_child = parent_conversation.get_child_conversation(child_id)

    assert retrieved_child is child_conversation


def test_get_nonexistent_child_conversation(test_agent, temp_dir):
    """Test retrieving a non-existent child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    nonexistent_id = uuid.uuid4()
    retrieved_child = parent_conversation.get_child_conversation(nonexistent_id)

    assert retrieved_child is None


def test_close_child_conversation(test_agent, child_agent, temp_dir):
    """Test closing a child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    child_conversation = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )

    child_id = child_conversation._state.id

    # Verify child exists in children.json before closing
    children_mapping = parent_conversation.get_children_mapping()
    assert str(child_id) in children_mapping

    # Mock the close method to track if it was called
    child_conversation.close = Mock()

    parent_conversation.close_child_conversation(child_id)

    # Check that child was closed and removed
    child_conversation.close.assert_called_once()
    assert child_id not in parent_conversation._child_conversations

    # Check that child was removed from children.json
    children_mapping = parent_conversation.get_children_mapping()
    assert str(child_id) not in children_mapping


def test_close_nonexistent_child_conversation(test_agent, temp_dir):
    """Test closing a non-existent child conversation."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    nonexistent_id = uuid.uuid4()

    # Should not raise an exception
    parent_conversation.close_child_conversation(nonexistent_id)


def test_list_child_conversations(test_agent, child_agent, temp_dir):
    """Test listing child conversation IDs."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    # Initially no children
    assert parent_conversation.list_child_conversations() == []

    # Create multiple children
    child1 = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )
    child2 = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )

    child_ids = parent_conversation.list_child_conversations()
    assert len(child_ids) == 2
    assert child1._state.id in child_ids
    assert child2._state.id in child_ids


def test_parent_conversation_close_closes_children(test_agent, child_agent, temp_dir):
    """Test that closing parent conversation closes all children."""
    parent_conversation = LocalConversation(
        agent=test_agent,
        working_dir=temp_dir,
        visualize=False,
    )

    # Create child conversations
    child1 = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )
    child2 = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )

    # Mock close methods
    child1.close = Mock()
    child2.close = Mock()

    # Close parent
    parent_conversation.close()

    # Check that children were closed
    child1.close.assert_called_once()
    child2.close.assert_called_once()

    # Check that children were removed from tracking
    assert len(parent_conversation._child_conversations) == 0


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
            working_dir=temp_dir,
            visualize=False,
        )

        child_conversation = parent_conversation.create_child_conversation(
            agent=agent,
            visualize=False,
        )

        child_id = child_conversation._state.id
        parent_id = parent_conversation._state.id

        # Check new directory structure: parent-uuid/child-uuid
        expected_path = os.path.join(
            temp_dir, ".conversations", str(parent_id), str(child_id)
        )
        assert child_conversation._state.working_dir == expected_path

        # Check children.json mapping contains correct agent type
        children_mapping = parent_conversation.get_children_mapping()
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
        working_dir=temp_dir,
        visualize=False,
    )

    # Create children
    execution_child = parent_conversation.create_child_conversation(
        agent=execution_agent,
        visualize=False,
    )
    planning_child = parent_conversation.create_child_conversation(
        agent=planning_agent,
        visualize=False,
    )

    # Both should exist simultaneously
    assert len(parent_conversation.list_child_conversations()) == 2

    # Should be in different directories under parent UUID
    execution_path = execution_child._state.working_dir
    planning_path = planning_child._state.working_dir
    parent_id = parent_conversation._state.id

    assert str(parent_id) in execution_path
    assert str(parent_id) in planning_path
    assert execution_path != planning_path

    # Both should be retrievable
    assert (
        parent_conversation.get_child_conversation(execution_child._state.id)
        is execution_child
    )
    assert (
        parent_conversation.get_child_conversation(planning_child._state.id)
        is planning_child
    )

    # Both should be in children.json mapping
    children_mapping = parent_conversation.get_children_mapping()
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
        working_dir=temp_dir,
        visualize=False,
    )

    # Initially no children
    children_mapping = parent_conversation.get_children_mapping()
    assert children_mapping == {}

    # Create a child
    child_conversation = parent_conversation.create_child_conversation(
        agent=child_agent,
        visualize=False,
    )
    child_id = child_conversation._state.id

    # Check mapping contains the child
    children_mapping = parent_conversation.get_children_mapping()
    assert str(child_id) in children_mapping
    assert children_mapping[str(child_id)]["agent_type"] == "child"
    assert children_mapping[str(child_id)]["agent_class"] == "ChildAgent"
    assert "created_at" in children_mapping[str(child_id)]

    # Clean up
    parent_conversation.close()
