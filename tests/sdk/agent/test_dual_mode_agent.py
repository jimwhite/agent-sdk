"""Tests for dual-mode agent functionality."""

import pytest

from openhands.sdk.agent import AgentMode, DualModeAgent, DualModeAgentConfig
from openhands.sdk.llm import LLM
from openhands.sdk.tool import ToolSpec


@pytest.fixture
def mock_planning_llm():
    """LLM for planning mode."""
    return LLM(model="gpt-4o-mini", service_id="planning-llm")


@pytest.fixture
def mock_execution_llm():
    """LLM for execution mode."""
    return LLM(model="claude-3-5-sonnet-20241022", service_id="execution-llm")


@pytest.fixture
def planning_tools():
    """Tools available in planning mode."""
    return [ToolSpec(name="ModeSwitchTool")]


@pytest.fixture
def execution_tools():
    """Tools available in execution mode."""
    return [ToolSpec(name="ModeSwitchTool")]  # In real usage, would include more tools


@pytest.fixture
def dual_mode_config(
    mock_planning_llm, mock_execution_llm, planning_tools, execution_tools
):
    """Configuration for dual-mode agent."""
    return DualModeAgentConfig(
        planning_llm=mock_planning_llm,
        execution_llm=mock_execution_llm,
        planning_tools=planning_tools,
        execution_tools=execution_tools,
        initial_mode=AgentMode.PLANNING,
    )


@pytest.fixture
def dual_mode_agent(dual_mode_config):
    """Create a dual-mode agent for testing."""
    return DualModeAgent(dual_mode_config=dual_mode_config)


def test_dual_mode_agent_initialization(dual_mode_agent, dual_mode_config):
    """Test that dual-mode agent initializes correctly."""
    assert dual_mode_agent.current_mode == AgentMode.PLANNING
    assert dual_mode_agent.dual_mode_config == dual_mode_config
    assert dual_mode_agent.llm == dual_mode_config.planning_llm
    assert dual_mode_agent.tools == dual_mode_config.planning_tools
    assert dual_mode_agent.system_prompt_filename == "system_prompt_planning.j2"


def test_dual_mode_agent_initialization_execution_mode(dual_mode_config):
    """Test initialization with execution mode."""
    dual_mode_config.initial_mode = AgentMode.EXECUTION
    agent = DualModeAgent(dual_mode_config=dual_mode_config)

    assert agent.current_mode == AgentMode.EXECUTION
    assert agent.llm == dual_mode_config.execution_llm
    assert agent.tools == dual_mode_config.execution_tools
    assert agent.system_prompt_filename == "system_prompt_execution.j2"


def test_switch_mode_planning_to_execution(dual_mode_agent, dual_mode_config):
    """Test switching from planning to execution mode."""
    # Start in planning mode
    assert dual_mode_agent.current_mode == AgentMode.PLANNING

    # Switch to execution mode
    observation = dual_mode_agent.switch_mode(AgentMode.EXECUTION)

    # Verify the switch
    assert observation.success is True
    assert observation.previous_mode == AgentMode.PLANNING
    assert observation.new_mode == AgentMode.EXECUTION
    assert dual_mode_agent.current_mode == AgentMode.EXECUTION
    assert dual_mode_agent.llm == dual_mode_config.execution_llm
    assert dual_mode_agent.tools == dual_mode_config.execution_tools


def test_switch_mode_execution_to_planning(dual_mode_config):
    """Test switching from execution to planning mode."""
    # Start in execution mode
    dual_mode_config.initial_mode = AgentMode.EXECUTION
    agent = DualModeAgent(dual_mode_config=dual_mode_config)
    assert agent.current_mode == AgentMode.EXECUTION

    # Switch to planning mode
    observation = agent.switch_mode(AgentMode.PLANNING)

    # Verify the switch
    assert observation.success is True
    assert observation.previous_mode == AgentMode.EXECUTION
    assert observation.new_mode == AgentMode.PLANNING
    assert agent.current_mode == AgentMode.PLANNING
    assert agent.llm == dual_mode_config.planning_llm
    assert agent.tools == dual_mode_config.planning_tools


def test_switch_mode_same_mode(dual_mode_agent):
    """Test switching to the same mode (should be no-op)."""
    # Already in planning mode
    assert dual_mode_agent.current_mode == AgentMode.PLANNING

    # Try to switch to planning mode again
    observation = dual_mode_agent.switch_mode(AgentMode.PLANNING)

    # Should succeed but not change anything
    assert observation.success is True
    assert observation.previous_mode == AgentMode.PLANNING
    assert observation.new_mode == AgentMode.PLANNING
    assert dual_mode_agent.current_mode == AgentMode.PLANNING


def test_mode_switch_action_handling(dual_mode_agent):
    """Test that mode switch actions are handled correctly."""
    # Test the mode switch directly
    initial_mode = dual_mode_agent.current_mode
    assert initial_mode == AgentMode.PLANNING

    # Switch to execution mode
    dual_mode_agent.switch_mode(AgentMode.EXECUTION)

    # Verify the mode was switched
    assert dual_mode_agent.current_mode == AgentMode.EXECUTION
    assert dual_mode_agent.llm == dual_mode_agent.dual_mode_config.execution_llm
    assert dual_mode_agent.tools == dual_mode_agent.dual_mode_config.execution_tools


def test_planning_mode_tool_restriction(dual_mode_agent):
    """Test that planning mode restricts tool execution."""
    # Ensure we're in planning mode
    assert dual_mode_agent.current_mode == AgentMode.PLANNING

    # Test that planning mode has restricted tools
    planning_tools = dual_mode_agent.tools
    execution_tools = dual_mode_agent.dual_mode_config.execution_tools

    # Planning tools should be a subset of execution tools (only mode switch allowed)
    assert len(planning_tools) <= len(execution_tools)

    # Verify that mode switch tool is available in planning mode
    planning_tool_names = [tool.name for tool in planning_tools]
    assert "ModeSwitchTool" in planning_tool_names


def test_execution_mode_allows_all_tools(dual_mode_config):
    """Test that execution mode allows all tools."""
    # Start in execution mode
    dual_mode_config.initial_mode = AgentMode.EXECUTION
    agent = DualModeAgent(dual_mode_config=dual_mode_config)

    # Verify we're in execution mode
    assert agent.current_mode == AgentMode.EXECUTION

    # Test that execution mode has all configured tools
    execution_tools = agent.tools
    expected_tools = dual_mode_config.execution_tools

    # Execution mode should have all the configured tools
    assert len(execution_tools) == len(expected_tools)

    # Verify that mode switch tool is available in execution mode
    execution_tool_names = [tool.name for tool in execution_tools]
    assert "ModeSwitchTool" in execution_tool_names


def test_agent_mode_enum():
    """Test AgentMode enum values."""
    assert AgentMode.PLANNING == "planning"
    assert AgentMode.EXECUTION == "execution"
    assert len(AgentMode) == 2


def test_dual_mode_config_validation():
    """Test DualModeAgentConfig validation."""
    planning_llm = LLM(model="gpt-4o-mini", service_id="planning-llm")
    execution_llm = LLM(model="claude-3-5-sonnet-20241022", service_id="execution-llm")
    tools = [ToolSpec(name="ModeSwitchTool")]

    config = DualModeAgentConfig(
        planning_llm=planning_llm,
        execution_llm=execution_llm,
        planning_tools=tools,
        execution_tools=tools,
        initial_mode=AgentMode.PLANNING,
    )

    assert config.planning_llm == planning_llm
    assert config.execution_llm == execution_llm
    assert config.planning_tools == tools
    assert config.execution_tools == tools
    assert config.initial_mode == AgentMode.PLANNING


def test_system_prompt_filename_updates_with_mode():
    """Test that system prompt filename updates when mode changes."""
    planning_llm = LLM(model="gpt-4o-mini", service_id="planning-llm")
    execution_llm = LLM(model="claude-3-5-sonnet-20241022", service_id="execution-llm")
    tools = [ToolSpec(name="ModeSwitchTool")]

    # Test planning mode
    config = DualModeAgentConfig(
        planning_llm=planning_llm,
        execution_llm=execution_llm,
        planning_tools=tools,
        execution_tools=tools,
        initial_mode=AgentMode.PLANNING,
    )
    agent = DualModeAgent(dual_mode_config=config)
    assert agent.system_prompt_filename == "system_prompt_planning.j2"

    # Test execution mode
    config.initial_mode = AgentMode.EXECUTION
    agent = DualModeAgent(dual_mode_config=config)
    assert agent.system_prompt_filename == "system_prompt_execution.j2"
