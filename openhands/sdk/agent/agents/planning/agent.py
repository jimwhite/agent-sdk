"""PlanningAgent - Read-only agent specialized in analysis and planning."""

from typing import Any

from openhands.sdk.agent.agent import Agent
from openhands.sdk.agent.base import AgentBase
from openhands.sdk.agent.config import AgentConfig
from openhands.sdk.agent.registry import register_agent
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import Tool, register_tool


logger = get_logger(__name__)

# Default LLM configuration for planning agent
DEFAULT_LLM = LLM(
    service_id="planning_agent_default",
    model="gpt-5-2025-08-07",
)


class PlanningAgent(Agent):
    """Read-only agent specialized in analysis and planning.

    Features:
    - Read-only access: FileEditorTool (view only)
    - Custom system prompt for planning tasks
    - No bash execution or file modification capabilities
    """

    def __init__(
        self,
        llm: LLM,
        **kwargs: Any,
    ):
        """Initialize PlanningAgent with read-only configuration.

        Args:
            llm: The LLM to use for the agent
            **kwargs: Additional configuration parameters
        """
        # Only read-only tools for planning agent
        tools = [
            Tool(name="FileEditorTool"),
            Tool(name="ExecutePlanTool"),
        ]

        # Use custom system prompt
        system_prompt_filename = "planning_system_prompt.j2"

        # Initialize with read-only defaults, allowing overrides
        super().__init__(
            llm=llm,
            tools=kwargs.pop("tools", tools),
            system_prompt_filename=kwargs.pop(
                "system_prompt_filename", system_prompt_filename
            ),
            # No MCP, security analyzer, or condenser by default for planning
            mcp_config=kwargs.pop("mcp_config", {}),
            security_analyzer=kwargs.pop("security_analyzer", None),
            condenser=kwargs.pop("condenser", None),
            # Override filter to be more restrictive - only allow file viewing and plan exec  # noqa: E501
            filter_tools_regex=kwargs.pop(
                "filter_tools_regex",
                "^(str_replace_editor|FileEditorTool|execute_plan|ExecutePlanTool)$",
            ),
            **kwargs,
        )


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

    def create(self, llm: LLM | None = None, **kwargs: Any) -> AgentBase:
        """Create a PlanningAgent instance.

        Args:
            llm: The LLM to use for the agent. If None, uses DEFAULT_LLM.
            **kwargs: Additional configuration parameters

        Returns:
            A PlanningAgent instance
        """
        # Register required tools
        self._register_tools()

        # Use default LLM if none provided
        if llm is None:
            llm = DEFAULT_LLM

        return PlanningAgent(llm=llm, **kwargs)

    def _register_tools(self) -> None:
        """Register the tools required by PlanningAgent."""
        try:
            from openhands.sdk.tool.tools.execute_plan import ExecutePlanTool
            from openhands.tools.str_replace_editor import FileEditorTool

            register_tool("FileEditorTool", FileEditorTool)
            register_tool("ExecutePlanTool", ExecutePlanTool)

        except ImportError as e:
            logger.warning(f"Failed to register some tools for PlanningAgent: {e}")


# Auto-register the configuration
try:
    register_agent(PlanningAgentConfig())
    logger.debug("PlanningAgentConfig registered successfully")
except Exception as e:
    logger.warning(f"Failed to register PlanningAgentConfig: {e}")
