"""Tests for Agent.init_state() in-place state modification behavior."""

from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import ConversationState
from openhands.sdk.event import SystemPromptEvent
from openhands.sdk.llm import LLM
from openhands.sdk.tool import Tool, register_tool
from openhands.sdk.workspace.local import LocalWorkspace
from openhands.tools.execute_bash import BashTool
from openhands.tools.execute_bash.impl import BashExecutor


@pytest.fixture
def llm() -> LLM:
    """Create a test LLM instance."""
    return LLM(
        model="gpt-4o-mini", api_key=SecretStr("test-key"), service_id="test-llm"
    )


@pytest.fixture
def workspace(tmp_path) -> LocalWorkspace:
    """Create a temporary workspace."""
    return LocalWorkspace(working_dir=str(tmp_path))


@pytest.fixture
def agent_with_bash(llm: LLM) -> Agent:
    """Create an agent with bash tool."""
    register_tool("BashTool", BashTool)
    return Agent(llm=llm, tools=[Tool(name="BashTool")])


@pytest.fixture
def agent_without_bash(llm: LLM) -> Agent:
    """Create an agent without bash tool."""
    return Agent(llm=llm, tools=[])


def test_init_state_modifies_state_in_place(
    agent_with_bash: Agent, workspace: LocalWorkspace
):
    """Test that init_state modifies the state object in-place, not creating a new one.

    This verifies the behavior documented in the base class:
    "NOTE: state will be mutated in-place."
    """
    # Create a conversation state
    state = ConversationState.create(
        id=uuid4(),
        agent=agent_with_bash,
        workspace=workspace,
        persistence_dir=None,
    )

    # Store the original object identity
    original_state_id = id(state)
    original_events_id = id(state.events)

    # Track events added via on_event callback
    events_added = []

    def on_event_callback(event):
        events_added.append(event)

    # Call init_state
    agent_with_bash.init_state(state, on_event=on_event_callback)

    # Verify that the state object identity hasn't changed (in-place modification)
    assert id(state) == original_state_id, "State object should be modified in-place"

    # Verify that the events list identity hasn't changed
    assert (
        id(state.events) == original_events_id
    ), "State.events should be modified in-place"

    # Verify that a SystemPromptEvent was added via on_event callback
    assert len(events_added) > 0, "At least one event should be added"
    assert any(
        isinstance(event, SystemPromptEvent) for event in events_added
    ), "A SystemPromptEvent should be added"


def test_init_state_configures_bash_tool_env_provider(
    agent_with_bash: Agent, workspace: LocalWorkspace
):
    """Test that init_state configures bash tools with env provider.

    This verifies that _configure_bash_tools_env_provider actually modifies
    the bash tool in the agent's tools_map.
    """
    # Create a conversation state
    state = ConversationState.create(
        id=uuid4(),
        agent=agent_with_bash,
        workspace=workspace,
        persistence_dir=None,
    )

    # Mock on_event callback
    on_event_callback = MagicMock()

    # Call init_state
    agent_with_bash.init_state(state, on_event=on_event_callback)

    # Get the bash tool from agent
    bash_tool = agent_with_bash.tools_map["execute_bash"]
    assert bash_tool is not None

    # Get the bash executor
    bash_executor = cast(BashExecutor, bash_tool.executor)

    # Verify that env_provider is configured
    assert (
        bash_executor.env_provider is not None
    ), "env_provider should be configured on bash tool"

    # Verify that env_masker is configured
    assert (
        bash_executor.env_masker is not None
    ), "env_masker should be configured on bash tool"

    # Test that env_provider is callable and returns a dict
    env_vars = bash_executor.env_provider("echo test")
    assert isinstance(env_vars, dict), "env_provider should return a dict"


def test_init_state_initializes_agent_tools(
    agent_with_bash: Agent, workspace: LocalWorkspace
):
    """Test that init_state initializes the agent's tools via _initialize().

    This verifies that the agent's _tools private attribute is populated.
    """
    # Create a conversation state
    state = ConversationState.create(
        id=uuid4(),
        agent=agent_with_bash,
        workspace=workspace,
        persistence_dir=None,
    )

    # Mock on_event callback
    on_event_callback = MagicMock()

    # Before init_state, the tools_map should raise an error
    # (agent not initialized)
    with pytest.raises(RuntimeError, match="Agent not initialized"):
        _ = agent_with_bash.tools_map

    # Call init_state
    agent_with_bash.init_state(state, on_event=on_event_callback)

    # After init_state, tools_map should be accessible
    tools_map = agent_with_bash.tools_map
    assert isinstance(tools_map, dict), "tools_map should be a dict"
    assert len(tools_map) > 0, "tools_map should not be empty"

    # Verify that bash tool is present
    assert "execute_bash" in tools_map, "execute_bash should be in tools_map"

    # Verify that built-in tools are present
    assert "finish" in tools_map, "finish should be in tools_map"
    assert "think" in tools_map, "think should be in tools_map"


def test_init_state_skips_reinitialization(
    agent_with_bash: Agent, workspace: LocalWorkspace
):
    """Test that init_state skips re-initialization if agent is already initialized.

    This verifies the behavior in AgentBase._initialize() that prevents
    re-initialization.
    """
    # Create a conversation state
    state = ConversationState.create(
        id=uuid4(),
        agent=agent_with_bash,
        workspace=workspace,
        persistence_dir=None,
    )

    # Mock on_event callback
    on_event_callback = MagicMock()

    # Call init_state first time
    agent_with_bash.init_state(state, on_event=on_event_callback)

    # Get the tools_map identity
    first_tools_map_id = id(agent_with_bash.tools_map)

    # Call init_state second time
    agent_with_bash.init_state(state, on_event=on_event_callback)

    # Verify that tools_map identity is the same (not re-initialized)
    second_tools_map_id = id(agent_with_bash.tools_map)
    assert (
        first_tools_map_id == second_tools_map_id
    ), "tools_map should not be re-initialized"


def test_init_state_without_bash_tool(
    agent_without_bash: Agent, workspace: LocalWorkspace
):
    """Test that init_state works correctly even without bash tool.

    This verifies that _configure_bash_tools_env_provider handles the case
    where no bash tool is present gracefully.
    """
    # Create a conversation state
    state = ConversationState.create(
        id=uuid4(),
        agent=agent_without_bash,
        workspace=workspace,
        persistence_dir=None,
    )

    # Mock on_event callback
    on_event_callback = MagicMock()

    # Call init_state - should not raise an error
    agent_without_bash.init_state(state, on_event=on_event_callback)

    # Verify that tools are initialized
    tools_map = agent_without_bash.tools_map
    assert isinstance(tools_map, dict), "tools_map should be a dict"

    # Verify that bash tool is not present
    assert "execute_bash" not in tools_map, "execute_bash should not be in tools_map"

    # Verify that built-in tools are still present
    assert "finish" in tools_map, "finish should be in tools_map"
    assert "think" in tools_map, "think should be in tools_map"


def test_init_state_adds_system_prompt_only_when_no_events(
    agent_with_bash: Agent, workspace: LocalWorkspace
):
    """Test that init_state only adds SystemPromptEvent when there are no existing events.

    This verifies the conditional logic in Agent.init_state() that checks for
    existing LLMConvertibleEvent instances.
    """
    # Create a conversation state
    state = ConversationState.create(
        id=uuid4(),
        agent=agent_with_bash,
        workspace=workspace,
        persistence_dir=None,
    )

    # Track events added via on_event callback
    events_added = []

    def on_event_callback(event):
        events_added.append(event)

    # Call init_state on fresh state (no events)
    agent_with_bash.init_state(state, on_event=on_event_callback)

    # Verify that a SystemPromptEvent was added
    assert len(events_added) == 1, "Exactly one event should be added"
    assert isinstance(
        events_added[0], SystemPromptEvent
    ), "A SystemPromptEvent should be added"

    # Now add the event to state.events
    for event in events_added:
        state.events.append(event)

    # Clear the events_added list
    events_added.clear()

    # Call init_state again (now there are events)
    # Create a new agent instance to avoid skipping re-initialization
    agent_with_bash_2 = Agent(
        llm=agent_with_bash.llm, tools=[Tool(name="BashTool")]
    )
    agent_with_bash_2.init_state(state, on_event=on_event_callback)

    # Verify that no new SystemPromptEvent was added
    system_prompt_events = [
        event for event in events_added if isinstance(event, SystemPromptEvent)
    ]
    assert (
        len(system_prompt_events) == 0
    ), "No new SystemPromptEvent should be added when events already exist"
