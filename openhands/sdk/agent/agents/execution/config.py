"""ExecutionAgent configuration."""

from typing import Any

from openhands.sdk.agent.agents.execution.agent import ExecutionAgent
from openhands.sdk.agent.base import AgentBase
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.agent.registry import register_agent
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import register_tool


logger = get_logger(__name__)


class ExecutionAgentConfig(AgentConfig):
    """Configuration for ExecutionAgent."""

    @property
    def name(self) -> str:
        return "execution"

    @property
    def description(self) -> str:
        return (
            "Full read-write agent with comprehensive tool access including "
            "bash execution, file editing, task tracking, and browser tools"
        )

    def create(self, llm: LLM, **kwargs: Any) -> AgentBase:
        """Create an ExecutionAgent instance.

        Args:
            llm: The LLM to use for the agent
            **kwargs: Additional configuration parameters

        Returns:
            An ExecutionAgent instance
        """
        # Register required tools
        self._register_tools(kwargs.get("enable_browser", True))

        return ExecutionAgent(llm=llm, **kwargs)

    def _register_tools(self, enable_browser: bool = True) -> None:
        """Register the tools required by ExecutionAgent."""
        try:
            from openhands.tools.execute_bash import BashTool
            from openhands.tools.str_replace_editor import FileEditorTool
            from openhands.tools.task_tracker import TaskTrackerTool

            # Core tools
            register_tool("BashTool", BashTool)
            register_tool("FileEditorTool", FileEditorTool)
            register_tool("TaskTrackerTool", TaskTrackerTool)

            if enable_browser:
                from openhands.tools.browser_use import BrowserToolSet

                register_tool("BrowserToolSet", BrowserToolSet)

            # Agent-specific tools (registered here to avoid import-time cycles)
            from openhands.sdk.tool.tools.spawn_planning_child import (
                SpawnPlanningChildTool,
            )

            register_tool("SpawnPlanningChildTool", SpawnPlanningChildTool)

        except ImportError as e:
            logger.warning(f"Failed to register some tools for ExecutionAgent: {e}")


# Auto-register the configuration
try:
    register_agent(ExecutionAgentConfig())
    logger.debug("ExecutionAgentConfig registered successfully")
except Exception as e:
    logger.warning(f"Failed to register ExecutionAgentConfig: {e}")
