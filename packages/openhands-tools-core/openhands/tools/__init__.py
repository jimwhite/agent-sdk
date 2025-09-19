"""OpenHands Tools - Plugin-based tool system with selective loading."""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, entry_points, version
from typing import TYPE_CHECKING, Any, Dict, List, Optional


__all__ = [
    "get_available_tools",
    "get_tool",
    "list_tool_names",
    "is_tool_available",
]

try:
    __version__ = version("openhands-tools-core")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for editable/unbuilt environments


def get_available_tools() -> Dict[str, Any]:
    """Get all available tool plugins that are currently installed.

    Returns:
        Dict mapping tool names to their entry point objects.
    """
    tools = {}
    try:
        eps = entry_points(group="openhands.tools")
        for ep in eps:
            try:
                tools[ep.name] = ep.load()
            except ImportError:
                # Tool dependencies not available, skip
                continue
    except Exception:
        # entry_points() might fail on older Python versions
        pass
    return tools


def get_tool(name: str) -> Optional[Any]:
    """Get a specific tool by name if available.

    Args:
        name: Tool name (e.g., 'bash', 'browser', 'editor')

    Returns:
        Tool class/object if available, None otherwise.
    """
    tools = get_available_tools()
    return tools.get(name)


def list_tool_names() -> List[str]:
    """List names of all available tools.

    Returns:
        List of tool names that are currently available.
    """
    return list(get_available_tools().keys())


def is_tool_available(name: str) -> bool:
    """Check if a specific tool is available.

    Args:
        name: Tool name to check

    Returns:
        True if tool is available, False otherwise.
    """
    return name in get_available_tools()


# Legacy compatibility - try to import from individual tool packages
def __getattr__(name: str):
    """Legacy compatibility for direct imports."""
    # Try to import from individual tool packages
    tool_mappings = {
        # Bash tool
        "BashTool": ("openhands.tools.bash", "BashTool"),
        "execute_bash_tool": ("openhands.tools.bash", "execute_bash_tool"),
        "ExecuteBashAction": ("openhands.tools.bash", "ExecuteBashAction"),
        "ExecuteBashObservation": ("openhands.tools.bash", "ExecuteBashObservation"),
        "BashExecutor": ("openhands.tools.bash", "BashExecutor"),
        # Editor tool
        "FileEditorTool": ("openhands.tools.editor", "FileEditorTool"),
        "str_replace_editor_tool": (
            "openhands.tools.editor",
            "str_replace_editor_tool",
        ),
        "StrReplaceEditorAction": ("openhands.tools.editor", "StrReplaceEditorAction"),
        "StrReplaceEditorObservation": (
            "openhands.tools.editor",
            "StrReplaceEditorObservation",
        ),
        "FileEditorExecutor": ("openhands.tools.editor", "FileEditorExecutor"),
        # Task tracker tool
        "TaskTrackerTool": ("openhands.tools.tracker", "TaskTrackerTool"),
        "task_tracker_tool": ("openhands.tools.tracker", "task_tracker_tool"),
        "TaskTrackerAction": ("openhands.tools.tracker", "TaskTrackerAction"),
        "TaskTrackerObservation": ("openhands.tools.tracker", "TaskTrackerObservation"),
        "TaskTrackerExecutor": ("openhands.tools.tracker", "TaskTrackerExecutor"),
        # Browser tool
        "BrowserToolSet": ("openhands.tools.browser", "BrowserToolSet"),
        "BrowserToolExecutor": ("openhands.tools.browser", "BrowserToolExecutor"),
    }

    if name in tool_mappings:
        mod_name, attr = tool_mappings[name]
        try:
            mod = import_module(mod_name)
            value = getattr(mod, attr)
            globals()[name] = value  # cache for next access
            return value
        except ImportError as e:
            # Extract tool name from module path
            tool_name = mod_name.split(".")[-1]
            raise ImportError(
                f"Tool '{tool_name}' is not available. "
                f"Install it with: pip install openhands-tools-{tool_name}"
            ) from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# For type checkers / IDEs (no runtime import):
if TYPE_CHECKING:
    # These imports will only work if the respective packages are installed
    try:
        from openhands.tools.bash import (
            BashExecutor,
            BashTool,
            ExecuteBashAction,
            ExecuteBashObservation,
            execute_bash_tool,
        )
    except ImportError:
        pass

    try:
        from openhands.tools.editor import (
            FileEditorExecutor,
            FileEditorTool,
            StrReplaceEditorAction,
            StrReplaceEditorObservation,
            str_replace_editor_tool,
        )
    except ImportError:
        pass

    try:
        from openhands.tools.tracker import (
            TaskTrackerAction,
            TaskTrackerExecutor,
            TaskTrackerObservation,
            TaskTrackerTool,
            task_tracker_tool,
        )
    except ImportError:
        pass

    try:
        from openhands.tools.browser import (
            BrowserToolExecutor,
            BrowserToolSet,
        )
    except ImportError:
        pass
