"""Tests for agent registry system."""

from typing import ClassVar
from unittest.mock import Mock

import pytest

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.agent.registry import (
    AgentRegistry,
    clear_registry,
    create_agent,
    list_agents,
    register_agent,
    unregister_agent,
)
from openhands.sdk.llm import LLM


class MockAgent(AgentBase):
    """Mock agent for testing."""

    agent_name: ClassVar[str] = "test"
    agent_description: ClassVar[str] = "Test agent"

    def __init__(self, llm: LLM, **kwargs):
        super().__init__(llm=llm, **kwargs)

    def step(self, state, on_event):
        """Mock step implementation."""
        pass


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    mock = Mock(spec=LLM)
    mock.openrouter_site_url = None
    mock.openrouter_app_name = None
    mock.openrouter_http_referer = None
    mock.aws_access_key_id = None
    mock.aws_secret_access_key = None
    mock.aws_region_name = None
    mock.model = "test-model"
    mock._metrics = None
    mock.log_completions = False
    mock.log_completions_folder = None
    mock.custom_tokenizer = None
    mock.base_url = None
    mock.reasoning_effort = None
    return mock


@pytest.fixture(autouse=True)
def clean_registry():
    """Clean the registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


def test_agent_registry_singleton():
    """Test that AgentRegistry is a singleton."""
    registry1 = AgentRegistry()
    registry2 = AgentRegistry()
    assert registry1 is registry2


def test_register_agent():
    """Test registering an agent class."""
    register_agent(MockAgent)

    agents = list_agents()
    assert "test" in agents
    assert agents["test"] == "Test agent"


def test_register_duplicate_agent_same_type():
    """Test re-registering the same agent class (should succeed)."""
    register_agent(MockAgent)
    register_agent(MockAgent)  # Should not raise - same class

    agents = list_agents()
    assert agents["test"] == "Test agent"


def test_register_duplicate_agent_different_type():
    """Test registering different agent types with same name (should fail)."""

    class AnotherMockAgent(AgentBase):
        agent_name: ClassVar[str] = "test"
        agent_description: ClassVar[str] = "Another test agent"

        def __init__(self, llm: LLM, **kwargs):
            super().__init__(llm=llm, **kwargs)

        def step(self, state, on_event):
            pass

    register_agent(MockAgent)

    with pytest.raises(ValueError, match="already registered with a different class"):
        register_agent(AnotherMockAgent)


def test_create_agent(mock_llm):
    """Test creating an agent by name."""
    register_agent(MockAgent)

    agent = create_agent("test", mock_llm, custom_param="value")

    assert agent is not None
    assert agent.llm is mock_llm


def test_create_nonexistent_agent(mock_llm):
    """Test creating a non-existent agent type."""
    with pytest.raises(ValueError, match="Agent type 'nonexistent' not found"):
        create_agent("nonexistent", mock_llm)


def test_list_agents():
    """Test listing registered agents."""

    class ListMockAgent1(AgentBase):
        agent_name: ClassVar[str] = "agent1"
        agent_description: ClassVar[str] = "First agent"

        def __init__(self, llm: LLM, **kwargs):
            super().__init__(llm=llm, **kwargs)

        def step(self, state, on_event):
            pass

    class ListMockAgent2(AgentBase):
        agent_name: ClassVar[str] = "agent2"
        agent_description: ClassVar[str] = "Second agent"

        def __init__(self, llm: LLM, **kwargs):
            super().__init__(llm=llm, **kwargs)

        def step(self, state, on_event):
            pass

    register_agent(ListMockAgent1)
    register_agent(ListMockAgent2)

    agents = list_agents()
    assert len(agents) == 2
    assert agents["agent1"] == "First agent"
    assert agents["agent2"] == "Second agent"


def test_unregister_agent():
    """Test unregistering an agent."""
    register_agent(MockAgent)

    assert "test" in list_agents()

    unregister_agent("test")

    assert "test" not in list_agents()


def test_unregister_nonexistent_agent():
    """Test unregistering a non-existent agent (should not raise)."""
    unregister_agent("nonexistent")  # Should not raise


def test_clear_registry():
    """Test clearing all agent registrations."""

    class ClearMockAgent1(AgentBase):
        agent_name: ClassVar[str] = "agent1"
        agent_description: ClassVar[str] = "First agent"

        def __init__(self, llm: LLM, **kwargs):
            super().__init__(llm=llm, **kwargs)

        def step(self, state, on_event):
            pass

    class ClearMockAgent2(AgentBase):
        agent_name: ClassVar[str] = "agent2"
        agent_description: ClassVar[str] = "Second agent"

        def __init__(self, llm: LLM, **kwargs):
            super().__init__(llm=llm, **kwargs)

        def step(self, state, on_event):
            pass

    register_agent(ClearMockAgent1)
    register_agent(ClearMockAgent2)

    assert len(list_agents()) == 2

    clear_registry()

    assert len(list_agents()) == 0


def test_thread_safety():
    """Test basic thread safety of registry operations."""
    import threading

    errors = []

    def register_and_create():
        try:
            register_agent(MockAgent)
            mock_llm = Mock(spec=LLM)
            mock_llm.openrouter_site_url = None
            mock_llm.openrouter_app_name = None
            mock_llm.openrouter_http_referer = None
            mock_llm.aws_access_key_id = None
            mock_llm.aws_secret_access_key = None
            mock_llm.aws_region_name = None
            mock_llm.model = "test-model"
            mock_llm._metrics = None
            mock_llm.log_completions = False
            mock_llm.log_completions_folder = None
            mock_llm.custom_tokenizer = None
            mock_llm.base_url = None
            mock_llm.reasoning_effort = None
            create_agent("test", mock_llm)
        except Exception as e:
            errors.append(e)

    # Run multiple threads concurrently
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=register_and_create)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    # Should not have any errors
    assert len(errors) == 0
    assert "test" in list_agents()
