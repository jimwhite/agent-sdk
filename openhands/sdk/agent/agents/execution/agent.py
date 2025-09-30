"""ExecutionAgent - Full read-write agent with comprehensive tool access."""

from typing import Any

from openhands.sdk.agent.agent import Agent
from openhands.sdk.context.condenser import LLMSummarizingCondenser
from openhands.sdk.llm import LLM
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import ToolSpec


class ExecutionAgent(Agent):
    """Full read-write agent with comprehensive tool access.

    Features:
    - Full read-write access: BashTool, FileEditorTool, TaskTrackerTool, BrowserToolSet
    - Security analyzer and context condenser enabled by default
    - MCP tools for external resource fetching
    """

    def __init__(
        self,
        llm: LLM,
        enable_browser: bool = True,
        enable_mcp: bool = True,
        **kwargs: Any,
    ):
        """Initialize ExecutionAgent with default configuration.

        Args:
            llm: The LLM to use for the agent
            enable_browser: Whether to enable browser tools
            enable_mcp: Whether to enable MCP tools
            **kwargs: Additional configuration parameters
        """
        # Default tools for execution agent
        tools = [
            ToolSpec(name="BashTool"),
            ToolSpec(name="FileEditorTool"),
            ToolSpec(name="TaskTrackerTool"),
            ToolSpec(name="SpawnPlanningChildTool"),
        ]

        if enable_browser:
            tools.append(ToolSpec(name="BrowserToolSet"))

        # Default MCP configuration
        mcp_config = {}
        if enable_mcp:
            mcp_config = {
                "mcpServers": {
                    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
                    "repomix": {
                        "command": "npx",
                        "args": ["-y", "repomix@1.4.2", "--mcp"],
                    },
                }
            }

        # Default condenser configuration
        condenser = LLMSummarizingCondenser(
            llm=llm.model_copy(update={"service_id": "condenser"}),
            max_size=80,
            keep_first=4,
        )

        # Initialize with defaults, allowing overrides
        super().__init__(
            llm=llm,
            tools=kwargs.pop("tools", tools),
            mcp_config=kwargs.pop("mcp_config", mcp_config),
            security_analyzer=kwargs.pop("security_analyzer", LLMSecurityAnalyzer()),
            condenser=kwargs.pop("condenser", condenser),
            **kwargs,
        )
