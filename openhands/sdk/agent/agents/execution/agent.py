"""Execution agent with full read-write toolkit.

Execution agents have read-write access to the codebase and can:
- Execute bash commands
- Modify files
- Create and manage tasks
- Browse the web (optional)
"""

from typing import Any

from openhands.sdk.agent.agent import Agent
from openhands.sdk.context.condenser import LLMSummarizingCondenser
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.tool import ToolSpec


logger = get_logger(__name__)


class ExecutionAgent(Agent):
    """Execution agent with full read-write toolkit."""

    def __init__(
        self,
        llm: LLM,
        enable_browser: bool = True,
        cli_mode: bool = False,
        **kwargs: Any,
    ):
        """Create an execution agent.

        Args:
            llm: The LLM to use for the agent
            enable_browser: Whether to include browser automation tools
            cli_mode: If True, disables browser tools
            **kwargs: Additional arguments passed to Agent.__init__
        """
        # Build tool specs
        tool_specs = [
            ToolSpec(name="BashTool"),
            ToolSpec(name="FileEditorTool"),
            ToolSpec(name="TaskTrackerTool"),
        ]

        # Add browser tools if enabled and not in CLI mode
        if enable_browser and not cli_mode:
            tool_specs.append(ToolSpec(name="BrowserToolSet"))

        # Set default kwargs if not provided
        if "mcp_config" not in kwargs:
            kwargs["mcp_config"] = {
                "mcpServers": {
                    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
                    "repomix": {
                        "command": "npx",
                        "args": ["-y", "repomix@1.4.2", "--mcp"],
                    },
                }
            }

        if "system_prompt_kwargs" not in kwargs:
            kwargs["system_prompt_kwargs"] = {"cli_mode": cli_mode}

        if "condenser" not in kwargs:
            kwargs["condenser"] = LLMSummarizingCondenser(
                llm=llm.model_copy(update={"service_id": "condenser"}),
                max_size=80,
                keep_first=4,
            )

        if "security_analyzer" not in kwargs:
            kwargs["security_analyzer"] = LLMSecurityAnalyzer()

        super().__init__(llm=llm, tools=tool_specs, **kwargs)

        logger.info(
            f"Created execution agent (browser={enable_browser and not cli_mode})"
        )
