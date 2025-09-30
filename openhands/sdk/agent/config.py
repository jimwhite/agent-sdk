"""Base configuration for agent types.

This module provides the AgentConfig base class for declaratively defining
agent configurations. Each agent type (execution, planning, review, etc.)
should create a config class that specifies its tools, prompts, and settings.
"""

from abc import ABC, abstractmethod
from typing import Any

from openhands.sdk.agent import Agent
from openhands.sdk.llm.llm import LLM


class AgentConfig(ABC):
    """Base class for agent configurations.

    Each agent type should subclass this and implement create() to return
    a configured Agent instance.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name for this agent type."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """A brief description of what this agent does."""
        ...

    @abstractmethod
    def create(self, llm: LLM, **kwargs: Any) -> Agent:
        """Create an agent instance with this configuration.

        Args:
            llm: The LLM to use for the agent
            **kwargs: Additional configuration options specific to this agent type

        Returns:
            A configured Agent instance
        """
        ...


__all__ = ["AgentConfig"]
