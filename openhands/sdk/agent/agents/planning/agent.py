"""PlanningAgent - Read-only agent specialized in analysis and planning."""

from typing import Any

from openhands.sdk.agent.agent import Agent
from openhands.sdk.llm import LLM
from openhands.sdk.tool import Tool


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
