"""Tests for mode switch tool."""

from openhands.sdk.agent.modes import AgentMode
from openhands.sdk.llm.message import TextContent
from openhands.sdk.tool.builtins.mode_switch import (
    ModeSwitchAction,
    ModeSwitchExecutor,
    ModeSwitchObservation,
    ModeSwitchTool,
)


def test_mode_switch_action_creation():
    """Test creating a mode switch action."""
    action = ModeSwitchAction(mode=AgentMode.EXECUTION, reason="Ready to implement")

    assert action.mode == AgentMode.EXECUTION
    assert action.reason == "Ready to implement"


def test_mode_switch_action_without_reason():
    """Test creating a mode switch action without reason."""
    action = ModeSwitchAction(mode=AgentMode.PLANNING)

    assert action.mode == AgentMode.PLANNING
    assert action.reason == ""


def test_mode_switch_action_visualize():
    """Test mode switch action visualization."""
    action = ModeSwitchAction(mode=AgentMode.EXECUTION, reason="Time to code")

    text = action.visualize
    assert "Switch to EXECUTION mode" in str(text)
    assert "Time to code" in str(text)


def test_mode_switch_action_visualize_no_reason():
    """Test mode switch action visualization without reason."""
    action = ModeSwitchAction(mode=AgentMode.PLANNING)

    text = action.visualize
    assert "Switch to PLANNING mode" in str(text)


def test_mode_switch_observation_creation():
    """Test creating a mode switch observation."""
    obs = ModeSwitchObservation(
        previous_mode=AgentMode.PLANNING,
        new_mode=AgentMode.EXECUTION,
        success=True,
        message="Successfully switched modes",
    )

    assert obs.previous_mode == AgentMode.PLANNING
    assert obs.new_mode == AgentMode.EXECUTION
    assert obs.success is True
    assert obs.message == "Successfully switched modes"


def test_mode_switch_observation_agent_observation():
    """Test mode switch observation agent_observation property."""
    obs = ModeSwitchObservation(
        previous_mode=AgentMode.PLANNING,
        new_mode=AgentMode.EXECUTION,
        success=True,
        message="Mode switched successfully",
    )

    agent_obs = obs.agent_observation
    assert len(agent_obs) == 1
    content = agent_obs[0]
    assert isinstance(content, TextContent)
    assert content.text == "Mode switched successfully"


def test_mode_switch_observation_visualize_success():
    """Test mode switch observation visualization for success."""
    obs = ModeSwitchObservation(
        previous_mode=AgentMode.PLANNING,
        new_mode=AgentMode.EXECUTION,
        success=True,
        message="Mode switched successfully",
    )

    text = obs.visualize
    text_str = str(text)
    assert "Successfully switched from PLANNING to EXECUTION mode" in text_str


def test_mode_switch_observation_visualize_failure():
    """Test mode switch observation visualization for failure."""
    obs = ModeSwitchObservation(
        previous_mode=AgentMode.PLANNING,
        new_mode=AgentMode.PLANNING,
        success=False,
        message="Failed to switch modes: error occurred",
    )

    text = obs.visualize
    text_str = str(text)
    assert "Failed to switch modes" in text_str


def test_mode_switch_executor():
    """Test mode switch executor."""
    executor = ModeSwitchExecutor()
    action = ModeSwitchAction(mode=AgentMode.EXECUTION, reason="Ready to implement")

    observation = executor(action)

    assert isinstance(observation, ModeSwitchObservation)
    assert observation.new_mode == AgentMode.EXECUTION
    assert observation.success is True
    assert "Mode switch to AgentMode.EXECUTION requested" in observation.message
    assert "Ready to implement" in observation.message


def test_mode_switch_executor_no_reason():
    """Test mode switch executor without reason."""
    executor = ModeSwitchExecutor()
    action = ModeSwitchAction(mode=AgentMode.PLANNING)

    observation = executor(action)

    assert isinstance(observation, ModeSwitchObservation)
    assert observation.new_mode == AgentMode.PLANNING
    assert observation.success is True
    assert observation.message == "Mode switch to AgentMode.PLANNING requested."


def test_mode_switch_tool_properties():
    """Test mode switch tool properties."""
    tool = ModeSwitchTool

    assert tool.name == "mode_switch"
    assert tool.action_type == ModeSwitchAction
    assert tool.observation_type == ModeSwitchObservation
    assert isinstance(tool.executor, ModeSwitchExecutor)
    assert "Switch the agent between planning and execution modes" in tool.description


def test_mode_switch_tool_annotations():
    """Test mode switch tool annotations."""
    tool = ModeSwitchTool

    assert tool.annotations is not None
    assert tool.annotations.title == "mode_switch"
    assert tool.annotations.readOnlyHint is True
    assert tool.annotations.destructiveHint is False
    assert tool.annotations.idempotentHint is True
    assert tool.annotations.openWorldHint is False


def test_mode_switch_tool_execution():
    """Test executing the mode switch tool."""
    tool = ModeSwitchTool
    action = ModeSwitchAction(mode=AgentMode.EXECUTION)

    observation = tool(action)

    assert isinstance(observation, ModeSwitchObservation)
    assert observation.new_mode == AgentMode.EXECUTION
    assert observation.success is True


def test_agent_mode_enum_in_actions():
    """Test that AgentMode enum works correctly in actions."""
    # Test both enum values
    planning_action = ModeSwitchAction(mode=AgentMode.PLANNING)
    execution_action = ModeSwitchAction(mode=AgentMode.EXECUTION)

    assert planning_action.mode == "planning"
    assert execution_action.mode == "execution"

    # Test that they're different
    assert planning_action.mode != execution_action.mode
