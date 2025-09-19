"""Tests for openhands.tools package initialization and import handling."""

import pytest


def test_submodule_imports_work():
    """Test that imports from submodules work correctly."""
    from openhands.tools.execute_bash import BashTool
    from openhands.tools.str_replace_editor import FileEditorTool

    # These should be importable without error
    assert BashTool is not None
    assert FileEditorTool is not None


def test_root_package_imports_no_longer_work():
    """Test that importing from root package no longer works (as intended)."""
    with pytest.raises(ImportError, match="cannot import name 'BashTool'"):
        from openhands.tools import BashTool  # noqa: F401 # type: ignore[attr-defined]

    with pytest.raises(ImportError, match="cannot import name 'FileEditorTool'"):
        from openhands.tools import (
            FileEditorTool,  # noqa: F401 # type: ignore[attr-defined]
        )


def test_attribute_access_no_longer_works():
    """Test that attribute access on root package no longer works."""
    import openhands.tools

    with pytest.raises(
        AttributeError,
        match=r"module 'openhands\.tools' has no attribute 'BashTool'",
    ):
        _ = openhands.tools.BashTool  # type: ignore[attr-defined]

    with pytest.raises(
        AttributeError,
        match=r"module 'openhands\.tools' has no attribute 'FileEditorTool'",
    ):
        _ = openhands.tools.FileEditorTool  # type: ignore[attr-defined]
