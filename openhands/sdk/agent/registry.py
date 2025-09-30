"""Thread-safe agent registry for dynamic agent instantiation."""

import threading
from typing import Any

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


class AgentRegistry:
    """Thread-safe singleton registry for agent configurations."""

    _instance: "AgentRegistry | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        if not hasattr(self, "_configs"):
            self._configs = {}  # type: dict[str, AgentConfig]
            self._registry_lock = threading.Lock()

    def __new__(cls) -> "AgentRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, config: AgentConfig) -> None:
        """Register an agent configuration.

        Args:
            config: The agent configuration to register

        Raises:
            ValueError: If an agent with the same name is already registered
        """
        with self._registry_lock:
            if config.name in self._configs:
                existing_config = self._configs[config.name]
                if existing_config.__class__ != config.__class__:
                    raise ValueError(
                        f"Agent '{config.name}' is already registered with a different "
                        f"configuration type: {existing_config.__class__.__name__} vs "
                        f"{config.__class__.__name__}"
                    )
                # Same config type, allow re-registration (for module reloading)
                logger.debug(f"Re-registering agent '{config.name}'")
            else:
                logger.debug(f"Registering agent '{config.name}'")

            self._configs[config.name] = config

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
            if name not in self._configs:
                available = list(self._configs.keys())
                raise ValueError(
                    f"Agent type '{name}' not found. Available types: {available}"
                )

            config = self._configs[name]
            return config.create(llm, **kwargs)

    def list_agents(self) -> dict[str, str]:
        """List all registered agent types and their descriptions.

        Returns:
            Dictionary mapping agent names to their descriptions
        """
        with self._registry_lock:
            return {name: config.description for name, config in self._configs.items()}

    def unregister(self, name: str) -> None:
        """Unregister an agent configuration.

        Args:
            name: The name of the agent type to unregister
        """
        with self._registry_lock:
            if name in self._configs:
                del self._configs[name]
                logger.debug(f"Unregistered agent '{name}'")

    def clear(self) -> None:
        """Clear all registered agent configurations. Used for testing."""
        with self._registry_lock:
            self._configs.clear()
            logger.debug("Cleared all agent registrations")


# Global registry instance
_registry = AgentRegistry()


def register_agent(config: AgentConfig) -> None:
    """Register an agent configuration with the global registry.

    Args:
        config: The agent configuration to register
    """
    _registry.register(config)


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
    """Unregister an agent configuration from the global registry.

    Args:
        name: The name of the agent type to unregister
    """
    _registry.unregister(name)


def clear_registry() -> None:
    """Clear all registered agent configurations. Used for testing."""
    _registry.clear()
