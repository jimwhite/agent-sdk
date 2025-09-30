"""OpenHands runtime package."""

from openhands.sdk.tool.builtins import BUILT_IN_TOOLS, FinishTool, ThinkTool
from openhands.sdk.tool.registry import (
    list_registered_tools,
    register_tool,
    resolve_tool,
)
from openhands.sdk.tool.schema import (
    ActionBase,
    ObservationBase,
)
from openhands.sdk.tool.spec import ToolSpec
from openhands.sdk.tool.tool import (
    ExecutableTool,
    Tool,
    ToolAnnotations,
    ToolBase,
    ToolExecutor,
)
from openhands.sdk.tool.tools.execute_plan import ExecutePlanTool
from openhands.sdk.tool.tools.spawn_planning_child import SpawnPlanningChildTool


# Register the new agent-specific tools
register_tool("SpawnPlanningChildTool", SpawnPlanningChildTool)
register_tool("ExecutePlanTool", ExecutePlanTool)


__all__ = [
    "Tool",
    "ToolBase",
    "ToolSpec",
    "ToolAnnotations",
    "ToolExecutor",
    "ExecutableTool",
    "ActionBase",
    "ObservationBase",
    "FinishTool",
    "ThinkTool",
    "BUILT_IN_TOOLS",
    "register_tool",
    "resolve_tool",
    "list_registered_tools",
]
