"""PlanningAgent configuration."""

from typing import Any

from openhands.sdk.agent.agents.planning.agent import PlanningAgent
from openhands.sdk.agent.base import AgentBase
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.agent.registry import register_agent
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import register_tool


logger = get_logger(__name__)


class PlanningAgentConfig(AgentConfig):
    """Configuration for PlanningAgent."""

    @property
    def name(self) -> str:
        return "planning"

    @property
    def description(self) -> str:
        return (
            "Read-only agent specialized in analysis and planning. "
            "Can view files and create detailed implementation plans."
        )

    def create(self, llm: LLM, **kwargs: Any) -> AgentBase:
        """Create a PlanningAgent instance.

        Args:
            llm: The LLM to use for the agent
            **kwargs: Additional configuration parameters

        Returns:
            A PlanningAgent instance
        """
        # Register required tools
        self._register_tools()

        return PlanningAgent(llm=llm, **kwargs)

    def _register_tools(self) -> None:
        """Register the tools required by PlanningAgent."""
        try:
            from openhands.tools.str_replace_editor import FileEditorTool

            register_tool("FileEditorTool", FileEditorTool)

        except ImportError as e:
            logger.warning(f"Failed to register some tools for PlanningAgent: {e}")


# Auto-register the configuration
try:
    register_agent(PlanningAgentConfig())
    logger.debug("PlanningAgentConfig registered successfully")
except Exception as e:
    logger.warning(f"Failed to register PlanningAgentConfig: {e}")
