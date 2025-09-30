"""Agent configuration system for dynamic agent instantiation."""

from abc import ABC, abstractmethod
from typing import Any

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.llm import LLM


class AgentConfig(ABC):
    """Abstract base class for agent configurations.

    Agent configurations define how to create specific agent types
    and provide metadata about the agent.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the agent type."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of the agent's capabilities."""
        pass

    @abstractmethod
    def create(self, llm: LLM, **kwargs: Any) -> AgentBase:
        """Create an instance of the agent.

        Args:
            llm: The LLM to use for the agent
            **kwargs: Additional configuration parameters

        Returns:
            An instance of the agent
        """
        pass
