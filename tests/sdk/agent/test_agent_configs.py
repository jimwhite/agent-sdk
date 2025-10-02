"""Tests for agent configurations."""

import pytest
from pydantic import SecretStr

from openhands.sdk.agent.agents.execution.agent import ExecutionAgent
from openhands.sdk.agent.agents.planning.agent import PlanningAgent


@pytest.fixture
def mock_llm():
    """Create a test LLM for testing."""
    from openhands.sdk.llm.llm import LLM

    return LLM(
        model="mock-model", api_key=SecretStr("mock-key"), service_id="test-service"
    )


def test_execution_agent_class_properties():
    """Test ExecutionAgent class properties."""
    assert ExecutionAgent.agent_name == "execution"
    assert "Full read-write agent" in ExecutionAgent.agent_description
    assert "bash execution" in ExecutionAgent.agent_description
    assert "file editing" in ExecutionAgent.agent_description


def test_planning_agent_class_properties():
    """Test PlanningAgent class properties."""
    assert PlanningAgent.agent_name == "planning"
    assert "Read-only agent" in PlanningAgent.agent_description
    assert "analysis and planning" in PlanningAgent.agent_description


def test_execution_agent_initialization(mock_llm):
    """Test ExecutionAgent initialization."""
    agent = ExecutionAgent(mock_llm, enable_browser=False, enable_mcp=False)

    assert agent.llm is mock_llm
    # Should have default tools
    tool_names = [tool.name for tool in agent.tools]
    assert "BashTool" in tool_names
    assert "FileEditorTool" in tool_names
    assert "TaskTrackerTool" in tool_names


def test_execution_agent_with_browser(mock_llm):
    """Test ExecutionAgent with browser enabled."""
    agent = ExecutionAgent(mock_llm, enable_browser=True, enable_mcp=False)

    tool_names = [tool.name for tool in agent.tools]
    assert "BrowserToolSet" in tool_names


def test_planning_agent_initialization(mock_llm):
    """Test PlanningAgent initialization."""
    agent = PlanningAgent(mock_llm)

    assert agent.llm is mock_llm
    # Should have FileEditorTool and ExecutePlanTool
    tool_names = [tool.name for tool in agent.tools]
    assert "FileEditorTool" in tool_names
    assert "ExecutePlanTool" in tool_names
    assert len(tool_names) == 2  # Two tools

    # Should have restrictive filter
    assert (
        agent.filter_tools_regex
        == "^(str_replace_editor|FileEditorTool|execute_plan|ExecutePlanTool)$"
    )


def test_planning_agent_system_prompt(mock_llm):
    """Test PlanningAgent uses custom system prompt."""
    agent = PlanningAgent(mock_llm)

    assert agent.system_prompt_filename == "planning_system_prompt.j2"


def test_execution_agent_has_security_features(mock_llm):
    """Test ExecutionAgent has security analyzer and condenser by default."""
    agent = ExecutionAgent(mock_llm, enable_mcp=False)

    # Should have security analyzer
    assert agent.security_analyzer is not None

    # Should have condenser
    assert agent.condenser is not None


def test_planning_agent_no_security_features(mock_llm):
    """Test PlanningAgent doesn't have security analyzer or condenser by default."""
    agent = PlanningAgent(mock_llm)

    # Should not have security analyzer
    assert agent.security_analyzer is None

    # Should not have condenser
    assert agent.condenser is None

    # Should not have MCP config
    assert agent.mcp_config == {}


def test_agent_override_defaults(mock_llm):
    """Test that agents can override default parameters."""
    # Test ExecutionAgent overrides
    custom_tools = []
    agent = ExecutionAgent(
        mock_llm,
        tools=custom_tools,
        security_analyzer=None,
        condenser=None,
        enable_mcp=False,
    )

    assert agent.tools == custom_tools
    assert agent.security_analyzer is None
    assert agent.condenser is None

    # Test PlanningAgent overrides
    custom_filter = "^custom_filter$"
    agent = PlanningAgent(mock_llm, filter_tools_regex=custom_filter)

    assert agent.filter_tools_regex == custom_filter
