"""Tests for agent registry system."""

from unittest.mock import Mock

import pytest

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.agent.registry import (
    AgentRegistry,
    clear_registry,
    create_agent,
    list_agents,
    register_agent,
    unregister_agent,
)
from openhands.sdk.llm import LLM


class MockAgentConfig(AgentConfig):
    """Mock agent configuration for testing."""

    def __init__(self, name: str, description: str):
        self._name = name
        self._description = description

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    def create(self, llm: LLM, **kwargs) -> AgentBase:
        mock_agent = Mock(spec=AgentBase)
        mock_agent.llm = llm
        mock_agent.__class__.__name__ = f"Mock{self._name.title()}Agent"
        return mock_agent


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    return Mock(spec=LLM)


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
    """Test registering an agent configuration."""
    config = MockAgentConfig("test", "Test agent")
    register_agent(config)

    agents = list_agents()
    assert "test" in agents
    assert agents["test"] == "Test agent"


def test_register_duplicate_agent_same_type():
    """Test re-registering the same agent type (should succeed)."""
    config1 = MockAgentConfig("test", "Test agent 1")
    config2 = MockAgentConfig("test", "Test agent 2")

    register_agent(config1)
    register_agent(config2)  # Should not raise

    agents = list_agents()
    assert agents["test"] == "Test agent 2"  # Latest registration wins


def test_register_duplicate_agent_different_type():
    """Test registering different config types with same name (should fail)."""

    class AnotherMockAgentConfig(AgentConfig):
        @property
        def name(self) -> str:
            return "test"

        @property
        def description(self) -> str:
            return "Another test agent"

        def create(self, llm: LLM, **kwargs) -> AgentBase:
            return Mock(spec=AgentBase)

    config1 = MockAgentConfig("test", "Test agent")
    config2 = AnotherMockAgentConfig()

    register_agent(config1)

    with pytest.raises(
        ValueError, match="already registered with a different configuration type"
    ):
        register_agent(config2)


def test_create_agent(mock_llm):
    """Test creating an agent by name."""
    config = MockAgentConfig("test", "Test agent")
    register_agent(config)

    agent = create_agent("test", mock_llm, custom_param="value")

    assert agent is not None
    assert agent.llm is mock_llm


def test_create_nonexistent_agent(mock_llm):
    """Test creating a non-existent agent type."""
    with pytest.raises(ValueError, match="Agent type 'nonexistent' not found"):
        create_agent("nonexistent", mock_llm)


def test_list_agents():
    """Test listing registered agents."""
    config1 = MockAgentConfig("agent1", "First agent")
    config2 = MockAgentConfig("agent2", "Second agent")

    register_agent(config1)
    register_agent(config2)

    agents = list_agents()
    assert len(agents) == 2
    assert agents["agent1"] == "First agent"
    assert agents["agent2"] == "Second agent"


def test_unregister_agent():
    """Test unregistering an agent."""
    config = MockAgentConfig("test", "Test agent")
    register_agent(config)

    assert "test" in list_agents()

    unregister_agent("test")

    assert "test" not in list_agents()


def test_unregister_nonexistent_agent():
    """Test unregistering a non-existent agent (should not raise)."""
    unregister_agent("nonexistent")  # Should not raise


def test_clear_registry():
    """Test clearing all agent registrations."""
    config1 = MockAgentConfig("agent1", "First agent")
    config2 = MockAgentConfig("agent2", "Second agent")

    register_agent(config1)
    register_agent(config2)

    assert len(list_agents()) == 2

    clear_registry()

    assert len(list_agents()) == 0


def test_thread_safety():
    """Test basic thread safety of registry operations."""
    import threading

    config = MockAgentConfig("test", "Test agent")
    errors = []

    def register_and_create():
        try:
            register_agent(config)
            mock_llm = Mock(spec=LLM)
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
