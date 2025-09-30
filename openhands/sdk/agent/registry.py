"""Agent registry for dynamic agent instantiation.

This module provides a centralized registry for discovering and creating
agents by name without needing to import specific factory functions.
"""

import threading
from typing import Any

from openhands.sdk.agent import Agent
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.llm.llm import LLM


class AgentRegistry:
    """Centralized registry for agent configurations.

    Usage:
        # Register an agent config
        AgentRegistry.register("execution", ExecutionAgentConfig())

        # Create an agent by name
        agent = AgentRegistry.create("execution", llm=my_llm)

        # List available agents
        agents = AgentRegistry.list_agents()
    """

    _agents: dict[str, AgentConfig] = {}
    _lock = threading.RLock()

    @classmethod
    def register(cls, name: str, config: AgentConfig) -> None:
        """Register an agent configuration.

        Args:
            name: Unique name for this agent type
            config: The AgentConfig instance defining this agent

        Raises:
            ValueError: If an agent with this name is already registered
        """
        with cls._lock:
            if name in cls._agents:
                raise ValueError(
                    f"Agent '{name}' is already registered. "
                    f"Use a different name or unregister the existing agent first."
                )
            cls._agents[name] = config

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister an agent configuration.

        Args:
            name: The name of the agent to remove

        Raises:
            KeyError: If no agent with this name is registered
        """
        with cls._lock:
            if name not in cls._agents:
                raise KeyError(f"No agent named '{name}' is registered")
            del cls._agents[name]

    @classmethod
    def create(cls, name: str, llm: LLM, **kwargs: Any) -> Agent:
        """Create an agent instance by name.

        Args:
            name: The name of the agent type to create
            llm: The LLM to use for the agent
            **kwargs: Additional configuration options specific to this agent type

        Returns:
            A configured Agent instance

        Raises:
            KeyError: If no agent with this name is registered
        """
        with cls._lock:
            if name not in cls._agents:
                available = ", ".join(cls._agents.keys())
                raise KeyError(
                    f"No agent named '{name}' is registered. "
                    f"Available agents: {available}"
                )
            config = cls._agents[name]
            return config.create(llm=llm, **kwargs)

    @classmethod
    def list_agents(cls) -> dict[str, str]:
        """List all registered agents with their descriptions.

        Returns:
            Dictionary mapping agent names to their descriptions
        """
        with cls._lock:
            return {name: config.description for name, config in cls._agents.items()}

    @classmethod
    def has_agent(cls, name: str) -> bool:
        """Check if an agent with the given name is registered.

        Args:
            name: The agent name to check

        Returns:
            True if the agent is registered, False otherwise
        """
        with cls._lock:
            return name in cls._agents

    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents.

        Warning: This is primarily for testing purposes.
        """
        with cls._lock:
            cls._agents.clear()


__all__ = ["AgentRegistry"]
