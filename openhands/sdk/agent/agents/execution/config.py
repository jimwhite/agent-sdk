"""Configuration for execution agents."""

from typing import Any

from openhands.sdk.agent.agents.execution.agent import ExecutionAgent
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.llm import LLM


class ExecutionAgentConfig(AgentConfig):
    """Configuration for execution agents with full read-write toolkit."""

    @property
    def name(self) -> str:
        return "execution"

    @property
    def description(self) -> str:
        return (
            "Full read-write agent for code implementation, "
            "execution, and system modifications"
        )

    def create(self, llm: LLM, **kwargs: Any) -> ExecutionAgent:
        """Create an execution agent with full read-write toolkit.

        Args:
            llm: The LLM to use for the execution agent
            **kwargs: All arguments are passed to ExecutionAgent:
                - enable_browser (bool): Whether to include browser automation tools
                    (default: True)
                - cli_mode (bool): If True, disables browser tools (default: False)
                - Plus any additional Agent kwargs (mcp_config, condenser, etc.)

        Returns:
            An ExecutionAgent configured for execution (full read-write access)
        """
        return ExecutionAgent(llm=llm, **kwargs)


__all__ = ["ExecutionAgentConfig"]
