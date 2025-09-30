"""Planning agent with read-only toolkit.

Planning agents have read-only access to the codebase and can:
- Read and analyze files
- Search and explore codebase structure
- Fetch external documentation
- Write detailed implementation plans

Planning agents CANNOT:
- Execute bash commands
- Modify files (except writing plans)
- Make any changes to the system
"""

from typing import Any

from openhands.sdk.agent.agent import Agent
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import ToolSpec


logger = get_logger(__name__)


class PlanningAgent(Agent):
    """Planning agent with read-only toolkit."""

    def __init__(
        self,
        llm: LLM,
        enable_condenser: bool = False,
        **kwargs: Any,
    ):
        """Create a planning agent.

        Args:
            llm: The LLM to use for the agent
            enable_condenser: Whether to enable context condensing
            **kwargs: Additional arguments passed to Agent.__init__
        """
        # Planning agent uses read-only tools
        tool_specs = [
            ToolSpec(name="FileEditorTool"),  # For reading files (view command)
        ]

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

        if "system_prompt_filename" not in kwargs:
            kwargs["system_prompt_filename"] = "planning_system_prompt.j2"

        if "system_prompt_kwargs" not in kwargs:
            kwargs["system_prompt_kwargs"] = {"planning_mode": True}

        # Optionally add condenser
        if enable_condenser and "condenser" not in kwargs:
            from openhands.sdk.context.condenser import LLMSummarizingCondenser

            kwargs["condenser"] = LLMSummarizingCondenser(
                llm=llm.model_copy(update={"service_id": "planning_condenser"}),
                max_size=60,
                keep_first=4,
            )

        super().__init__(llm=llm, tools=tool_specs, **kwargs)

        logger.info("Created planning agent (read-only mode)")
