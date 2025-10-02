"""Fixtures for plan writer tool tests."""

import tempfile
from pathlib import Path

import pytest

from openhands.tools.plan_writer.impl import PlanWriterExecutor


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        yield workspace


@pytest.fixture
def plan_writer_executor(temp_workspace):
    """Create a PlanWriterExecutor for testing."""
    return PlanWriterExecutor(workspace_root=str(temp_workspace))
