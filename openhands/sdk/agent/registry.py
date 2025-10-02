"""Thread-safe agent registry for dynamic agent instantiation."""

import threading
from typing import Any

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


class AgentRegistry:
    """Thread-safe singleton registry for agent classes."""

    _instance: "AgentRegistry | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        if not hasattr(self, "_agents"):
            self._agents: dict[str, type[AgentBase]] = {}
            self._registry_lock = threading.Lock()

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, agent_class: type[AgentBase]) -> None:
        """Register an agent class.

        Args:
            agent_class: The agent class to register

        Raises:
            ValueError: If an agent with the same name is already registered
        """
        with self._registry_lock:
            name: str = getattr(agent_class, "agent_name", agent_class.__name__.lower())
            if name in self._agents:
                existing_class = self._agents[name]
                if existing_class != agent_class:
                    raise ValueError(
                        f"Agent '{name}' is already registered with a different "
                        f"class: {existing_class.__name__} vs "
                        f"{agent_class.__name__}"
                    )
                # Same class, allow re-registration (for module reloading)
                logger.debug(f"Re-registering agent '{name}'")
            else:
                logger.debug(f"Registering agent '{name}'")

            self._agents[name] = agent_class

    def create(self, name: str, llm: LLM, **kwargs: Any) -> AgentBase:
        """Create an agent instance by name.

        Args:
            name: The name of the agent type to create
            llm: The LLM to use for the agent
            **kwargs: Additional configuration parameters

        Returns:
            An instance of the requested agent type

        Raises:
            ValueError: If the agent type is not registered
        """
        with self._registry_lock:
            if name not in self._agents:
                available = list(self._agents.keys())
                raise ValueError(
                    f"Agent type '{name}' not found. Available types: {available}"
                )

            agent_class = self._agents[name]
            return agent_class(llm=llm, **kwargs)

    def list_agents(self) -> dict[str, str]:
        """List all registered agent types and their descriptions.

        Returns:
            Dictionary mapping agent names to their descriptions
        """
        with self._registry_lock:
            return {
                name: getattr(
                    agent_class, "agent_description", "No description available"
                )
                for name, agent_class in self._agents.items()
            }

    def unregister(self, name: str) -> None:
        """Unregister an agent class.

        Args:
            name: The name of the agent type to unregister
        """
        with self._registry_lock:
            if name in self._agents:
                del self._agents[name]
                logger.debug(f"Unregistered agent '{name}'")

    def clear(self) -> None:
        """Clear all registered agent classes. Used for testing."""
        with self._registry_lock:
            self._agents.clear()
            logger.debug("Cleared all agent registrations")


# Global registry instance
_registry = AgentRegistry()


def register_agent(agent_class: type[AgentBase]) -> None:
    """Register an agent class with the global registry.

    Args:
        agent_class: The agent class to register
    """
    _registry.register(agent_class)


def create_agent(name: str, llm: LLM, **kwargs: Any) -> AgentBase:
    """Create an agent instance by name using the global registry.

    Args:
        name: The name of the agent type to create
        llm: The LLM to use for the agent
        **kwargs: Additional configuration parameters

    Returns:
        An instance of the requested agent type
    """
    return _registry.create(name, llm, **kwargs)


def list_agents() -> dict[str, str]:
    """List all registered agent types and their descriptions.

    Returns:
        Dictionary mapping agent names to their descriptions
    """
    return _registry.list_agents()


def unregister_agent(name: str) -> None:
    """Unregister an agent class from the global registry.

    Args:
        name: The name of the agent type to unregister
    """
    _registry.unregister(name)


def clear_registry() -> None:
    """Clear all registered agent classes. Used for testing."""
    _registry.clear()
