"""Runtime tools package."""

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING


try:
    __version__ = version("openhands-tools")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for editable/unbuilt environments


_mapping = {
    # execute_bash
    "ExecuteBashAction": ("openhands.tools.execute_bash", "ExecuteBashAction"),
    "ExecuteBashObservation": (
        "openhands.tools.execute_bash",
        "ExecuteBashObservation",
    ),
    "BashExecutor": ("openhands.tools.execute_bash", "BashExecutor"),
    "BashTool": ("openhands.tools.execute_bash", "BashTool"),
    # str_replace_editor
    "StrReplaceEditorAction": (
        "openhands.tools.str_replace_editor",
        "StrReplaceEditorAction",
    ),
    "StrReplaceEditorObservation": (
        "openhands.tools.str_replace_editor",
        "StrReplaceEditorObservation",
    ),
    "FileEditorExecutor": ("openhands.tools.str_replace_editor", "FileEditorExecutor"),
    "FileEditorTool": ("openhands.tools.str_replace_editor", "FileEditorTool"),
    # task_tracker
    "task_tracker_tool": ("openhands.tools.task_tracker", "task_tracker_tool"),
    "TaskTrackerAction": ("openhands.tools.task_tracker", "TaskTrackerAction"),
    "TaskTrackerObservation": (
        "openhands.tools.task_tracker",
        "TaskTrackerObservation",
    ),
    "TaskTrackerExecutor": ("openhands.tools.task_tracker", "TaskTrackerExecutor"),
    "TaskTrackerTool": ("openhands.tools.task_tracker", "TaskTrackerTool"),
    # browser_use (heavy; only loads if you actually touch it)
    "BrowserToolSet": ("openhands.tools.browser_use", "BrowserToolSet"),
}


def __getattr__(name: str):
    if name in _mapping:
        mod_name, attr = _mapping[name]
        mod = import_module(mod_name)
        value = getattr(mod, attr)
        globals()[name] = value  # cache for next access
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# For type checkers / IDEs (no runtime import):
if TYPE_CHECKING:
    from openhands.tools.browser_use import BrowserToolSet
    from openhands.tools.execute_bash import (
        BashExecutor,
        BashTool,
        ExecuteBashAction,
        ExecuteBashObservation,
    )
    from openhands.tools.str_replace_editor import (
        FileEditorExecutor,
        FileEditorTool,
        StrReplaceEditorAction,
        StrReplaceEditorObservation,
    )
    from openhands.tools.task_tracker import (
        TaskTrackerExecutor,
        TaskTrackerTool,
    )

    __all__ = [
        "BrowserToolSet",
        "BashExecutor",
        "BashTool",
        "ExecuteBashAction",
        "ExecuteBashObservation",
        "FileEditorExecutor",
        "FileEditorTool",
        "StrReplaceEditorAction",
        "StrReplaceEditorObservation",
        "TaskTrackerExecutor",
        "TaskTrackerTool",
    ]
