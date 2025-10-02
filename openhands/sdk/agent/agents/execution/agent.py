"""ExecutionAgent - Full read-write agent with comprehensive tool access."""

from typing import Any, ClassVar

from openhands.sdk.agent.agent import Agent
from openhands.sdk.context.condenser import LLMSummarizingCondenser
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import Tool, register_tool


logger = get_logger(__name__)


class ExecutionAgent(Agent):
    """Full read-write agent with comprehensive tool access.

    Features:
    - Full read-write access: BashTool, FileEditorTool, TaskTrackerTool, BrowserToolSet
    - Security analyzer and context condenser enabled by default
    - MCP tools for external resource fetching
    """

    # Agent configuration
    agent_name: ClassVar[str] = "execution"
    agent_description: ClassVar[str] = (
        "Full read-write agent with comprehensive tool access including "
        "bash execution, file editing, task tracking, and browser tools"
    )

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
        # Register required tools
        self._register_tools(enable_browser)

        # Default tools for execution agent
        tools = [
            Tool(name="BashTool"),
            Tool(name="FileEditorTool"),
            Tool(name="TaskTrackerTool"),
            Tool(name="SpawnPlanningChildTool"),
        ]

        if enable_browser:
            tools.append(Tool(name="BrowserToolSet"))

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
            from openhands.sdk.tool.tools.agent_dispatcher import AgentDispatcher

            # Register planning child tool resolver with conversation ID
            def spawn_planning_child_resolver(conv_state, **params):
                dispatcher = AgentDispatcher()
                return [dispatcher.create_spawn_tool("planning", conv_state)]

            register_tool("SpawnPlanningChildTool", spawn_planning_child_resolver)

        except ImportError as e:
            logger.warning(f"Failed to register some tools for ExecutionAgent: {e}")


# Auto-register the agent
try:
    from openhands.sdk.agent.registry import register_agent

    register_agent(ExecutionAgent)
    logger.debug("ExecutionAgent registered successfully")
except Exception as e:
    logger.warning(f"Failed to register ExecutionAgent: {e}")
