"""Runtime tools package."""

from openhands.tools.browser_use import BrowserToolExecutor, BrowserToolSet
from openhands.tools.execute_bash import BashExecutor, BashTool
from openhands.tools.str_replace_editor import FileEditorExecutor, FileEditorTool
from openhands.tools.task_tracker import TaskTrackerExecutor, TaskTrackerTool


__all__ = [
    "BashExecutor",
    "BashTool",
    "FileEditorExecutor",
    "FileEditorTool",
    "TaskTrackerExecutor",
    "TaskTrackerTool",
    "BrowserToolExecutor",
    "BrowserToolSet",
]

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("openhands-tools")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for editable/unbuilt environments
