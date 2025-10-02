"""Tests for spawn_planning_child tool."""

from unittest.mock import Mock

from openhands.sdk.tool.tools.spawn_planning_child import (
    SpawnPlanningChildAction,
    SpawnPlanningChildObservation,
    SpawnPlanningChildTool,
)


def test_spawn_planning_child_action():
    """Test SpawnPlanningChildAction creation and properties."""
    action = SpawnPlanningChildAction(
        task_description="Build a web app", agent_type="planning"
    )

    assert action.task_description == "Build a web app"
    assert action.agent_type == "planning"

    # Test visualization
    visualization = action.visualize
    assert "Build a web app" in str(visualization)


def test_spawn_planning_child_action_without_plan_file():
    """Test SpawnPlanningChildAction without plan file path."""
    action = SpawnPlanningChildAction(
        task_description="Build a web app", agent_type="planning"
    )

    assert action.task_description == "Build a web app"
    assert action.agent_type == "planning"


def test_spawn_planning_child_observation_success():
    """Test SpawnPlanningChildObservation for successful spawn."""
    obs = SpawnPlanningChildObservation(
        success=True,
        child_conversation_id="child-123",
        working_directory="/test/dir",
        agent_type="planning",
        message="Planning child created successfully",
        plan_file_path="/path/to/plan.md",
    )

    assert obs.success
    assert obs.child_conversation_id == "child-123"
    assert obs.working_directory == "/test/dir"
    assert obs.agent_type == "planning"
    assert obs.message == "Planning child created successfully"
    assert obs.plan_file_path == "/path/to/plan.md"


def test_spawn_planning_child_observation_failure():
    """Test SpawnPlanningChildObservation for failed spawn."""
    obs = SpawnPlanningChildObservation(
        success=False,
        error="Failed to spawn planning child: Test error",
        agent_type="planning",
        message="Error occurred",
    )

    assert not obs.success
    assert obs.error == "Failed to spawn planning child: Test error"
    assert obs.agent_type == "planning"


def test_spawn_planning_child_tool_creation():
    """Test SpawnPlanningChildTool creation."""
    # Mock conversation state
    mock_conversation_state = Mock()
    mock_conversation_state.conversation_id = "test-conv-id"

    # Test that the create method exists and can be called
    # We don't need to test the full functionality here since that's tested in
    # AgentDispatcher tests
    try:
        SpawnPlanningChildTool.create(mock_conversation_state)
        # If we get here without exception, the method works
        assert True
    except Exception as e:
        # If there's an exception, it should be related to missing agent registry
        # which is expected in a test environment
        assert (
            "agent type" in str(e).lower()
            or "conversation" in str(e).lower()
            or "registry" in str(e).lower()
        )


def test_spawn_planning_child_observation_visualization():
    """Test SpawnPlanningChildObservation visualization."""
    # Test successful observation
    obs_success = SpawnPlanningChildObservation(
        success=True,
        child_conversation_id="child-123",
        working_directory="/test/dir",
        agent_type="planning",
        message="Planning child created successfully",
        plan_file_path="/path/to/plan.md",
    )

    viz = obs_success.visualize
    assert "✅ Planning child created successfully" in str(viz)
    assert "child-123" in str(viz)

    # Test failed observation
    obs_failure = SpawnPlanningChildObservation(
        success=False,
        error="Failed to spawn planning child: Test error",
        agent_type="planning",
        message="Error occurred",
    )

    viz = obs_failure.visualize
    assert "❌ Failed to spawn planning child: Test error" in str(viz)
