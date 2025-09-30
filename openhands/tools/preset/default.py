"""Preset configurations for OpenHands agents.

This module provides convenient preset configurations for creating agents:
- get_execution_agent: Full read-write agent for implementation
- get_planning_agent: Read-only agent for research and planning

For more control, use the AgentRegistry directly:
- AgentRegistry.create("execution", llm, **kwargs)
- AgentRegistry.create("planning", llm, **kwargs)
"""

from openhands.sdk.agent.registry import AgentRegistry
from openhands.sdk.llm.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import ToolSpec, register_tool


logger = get_logger(__name__)


def register_default_tools(enable_browser: bool = True) -> None:
    """Register the default set of tools."""
    from openhands.tools.execute_bash import BashTool
    from openhands.tools.str_replace_editor import FileEditorTool
    from openhands.tools.task_tracker import TaskTrackerTool

    register_tool("BashTool", BashTool)
    logger.debug("Tool: BashTool registered.")
    register_tool("FileEditorTool", FileEditorTool)
    logger.debug("Tool: FileEditorTool registered.")
    register_tool("TaskTrackerTool", TaskTrackerTool)
    logger.debug("Tool: TaskTrackerTool registered.")

    if enable_browser:
        from openhands.tools.browser_use import BrowserToolSet

        register_tool("BrowserToolSet", BrowserToolSet)
        logger.debug("Tool: BrowserToolSet registered.")


def get_default_tools(
    enable_browser: bool = True,
) -> list[ToolSpec]:
    """Get the default set of tool specifications for the standard experience.

    Args:
        enable_browser: Whether to include browser tools.
    """
    register_default_tools(enable_browser=enable_browser)

    tool_specs = [
        ToolSpec(name="BashTool"),
        ToolSpec(name="FileEditorTool"),
        ToolSpec(name="TaskTrackerTool"),
    ]
    if enable_browser:
        tool_specs.append(ToolSpec(name="BrowserToolSet"))
    return tool_specs


def get_execution_agent(
    llm: LLM,
    cli_mode: bool = False,
    enable_browser: bool = True,
):
    """Get an execution agent with full read-write toolkit.

    This is a convenience wrapper that uses AgentRegistry and handles
    tool registration automatically.

    Args:
        llm: The LLM to use for the agent
        cli_mode: If True, disables browser tools
        enable_browser: Whether to include browser tools (overridden by cli_mode)

    Returns:
        An execution agent configured with the specified tools
    """
    # Register tools first
    register_default_tools(enable_browser=enable_browser and not cli_mode)

    # Use the AgentRegistry to create the agent
    return AgentRegistry.create(
        "execution",
        llm=llm,
        enable_browser=enable_browser,
        cli_mode=cli_mode,
    )


def get_planning_agent(
    llm: LLM,
    enable_condenser: bool = False,
):
    """Get a planning agent with read-only toolkit.

    This is a convenience wrapper that uses AgentRegistry and handles
    tool registration automatically.

    Args:
        llm: The LLM to use for the planning agent
        enable_condenser: Whether to enable context condensing (usually not needed)

    Returns:
        A planning agent configured for read-only research and planning
    """
    # Register tools (no browser for planning agents)
    register_default_tools(enable_browser=False)

    # Use the AgentRegistry to create the agent
    return AgentRegistry.create(
        "planning",
        llm=llm,
        enable_condenser=enable_condenser,
    )


get_default_agent = get_execution_agent
