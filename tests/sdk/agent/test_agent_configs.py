"""Tests for agent configurations."""

from unittest.mock import patch

import pytest
from pydantic import SecretStr

from openhands.sdk.agent.agents.execution.agent import ExecutionAgent
from openhands.sdk.agent.agents.execution.config import ExecutionAgentConfig
from openhands.sdk.agent.agents.planning.agent import PlanningAgent
from openhands.sdk.agent.agents.planning.config import PlanningAgentConfig


@pytest.fixture
def mock_llm():
    """Create a test LLM for testing."""
    from openhands.sdk.llm.llm import LLM

    return LLM(
        model="mock-model", api_key=SecretStr("mock-key"), service_id="test-service"
    )


def test_execution_agent_config_properties():
    """Test ExecutionAgentConfig properties."""
    config = ExecutionAgentConfig()

    assert config.name == "execution"
    assert "Full read-write agent" in config.description
    assert "bash execution" in config.description
    assert "file editing" in config.description


def test_planning_agent_config_properties():
    """Test PlanningAgentConfig properties."""
    config = PlanningAgentConfig()

    assert config.name == "planning"
    assert "Read-only agent" in config.description
    assert "analysis and planning" in config.description


@patch("openhands.sdk.agent.agents.execution.config.register_tool")
def test_execution_agent_config_create(mock_register_tool, mock_llm):
    """Test ExecutionAgentConfig.create method."""
    config = ExecutionAgentConfig()

    agent = config.create(mock_llm, enable_browser=True)

    assert isinstance(agent, ExecutionAgent)
    assert agent.llm is mock_llm

    # Verify tools were registered
    assert (
        mock_register_tool.call_count >= 3
    )  # At least BashTool, FileEditorTool, TaskTrackerTool


@patch("openhands.sdk.agent.agents.execution.config.register_tool")
def test_execution_agent_config_create_no_browser(mock_register_tool, mock_llm):
    """Test ExecutionAgentConfig.create without browser tools."""
    config = ExecutionAgentConfig()

    agent = config.create(mock_llm, enable_browser=False)

    assert isinstance(agent, ExecutionAgent)
    assert agent.llm is mock_llm


@patch("openhands.sdk.agent.agents.planning.config.register_tool")
def test_planning_agent_config_create(mock_register_tool, mock_llm):
    """Test PlanningAgentConfig.create method."""
    config = PlanningAgentConfig()

    agent = config.create(mock_llm)

    assert isinstance(agent, PlanningAgent)
    assert agent.llm is mock_llm

    # Verify FileEditorTool was registered
    mock_register_tool.assert_called()


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


def test_agent_config_override_defaults(mock_llm):
    """Test that agent configs can override default parameters."""
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
