"""Tests for openhands_tools package initialization and import handling."""

import pytest


def test_submodule_imports_work():
    """Tools should be imported via explicit submodules."""
    from openhands_tools.browser_use import BrowserToolSet
    from openhands_tools.execute_bash import BashTool
    from openhands_tools.file_editor import FileEditorTool
    from openhands_tools.task_tracker import TaskTrackerTool

    assert BashTool is not None
    assert FileEditorTool is not None
    assert TaskTrackerTool is not None
    assert BrowserToolSet is not None


def test_tools_module_has_no_direct_exports():
    """Accessing tools via openhands_tools should fail."""
    import openhands_tools

    assert not hasattr(openhands_tools, "BashTool")
    with pytest.raises(AttributeError):
        _ = openhands_tools.BashTool  # type: ignore[attr-defined]


def test_from_import_raises_import_error():
    """`from openhands_tools import X` should fail fast."""

    with pytest.raises(ImportError):
        from openhand.tools import BashTool  # type: ignore[import] # noqa: F401
