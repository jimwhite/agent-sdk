"""Configuration for planning agents."""

from typing import Any

from openhands.sdk.agent.agents.planning.agent import PlanningAgent
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.llm import LLM


class PlanningAgentConfig(AgentConfig):
    """Configuration for planning agents with read-only toolkit."""

    @property
    def name(self) -> str:
        return "planning"

    @property
    def description(self) -> str:
        return (
            "Read-only agent for research, analysis, and creating implementation plans"
        )

    def create(self, llm: LLM, **kwargs: Any) -> PlanningAgent:
        """Create a planning agent with read-only toolkit.

        Args:
            llm: The LLM to use for the planning agent
            **kwargs: All arguments are passed to PlanningAgent:
                - enable_condenser (bool): Whether to enable context condensing
                - Plus any additional Agent kwargs (mcp_config, etc.)

        Returns:
            A PlanningAgent configured for planning (read-only analysis)
        """
        return PlanningAgent(llm=llm, **kwargs)


__all__ = ["PlanningAgentConfig"]
