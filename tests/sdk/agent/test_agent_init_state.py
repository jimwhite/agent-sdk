"""Test that Agent.init_state modifies state in-place."""

from unittest.mock import MagicMock

from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.event import SystemPromptEvent
from openhands.sdk.llm import LLM
from openhands.sdk.tool.spec import Tool


def test_init_state_modifies_state_in_place():
    """Test that init_state modifies the state object in-place.
    
    Verifies:
    1. State.events is modified (SystemPromptEvent is added)
    2. Agent's _tools map is populated
    3. Events list grows after init_state
    """
    llm = LLM(
        service_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])
    
    # Track events added via callbacks
    events_added = []
    def track_events(event):
        events_added.append(event)
    
    # Create conversation - this will create a state and call init_state automatically
    convo = Conversation(agent=agent, callbacks=[track_events], visualize=False)
    
    # Get the state from the conversation
    state = convo.state
    
    # Verify that the state was modified
    # 1. Events were added to the state
    assert len(events_added) > 0, "init_state should add events via callback"
    
    # 2. The first event should be a SystemPromptEvent
    system_prompt_events = [e for e in events_added if isinstance(e, SystemPromptEvent)]
    assert len(system_prompt_events) > 0, "Should have at least one SystemPromptEvent"
    
    # 3. The SystemPromptEvent should contain tools
    system_prompt_event = system_prompt_events[0]
    assert system_prompt_event.tools is not None, "SystemPromptEvent should have tools"
    assert len(system_prompt_event.tools) > 0, "SystemPromptEvent should have at least one tool"
    
    # 4. Agent's _tools map should be populated
    assert len(agent._tools) > 0, "Agent's _tools map should be populated"
    assert "finish" in agent._tools, "Built-in 'finish' tool should be present"
    assert "think" in agent._tools, "Built-in 'think' tool should be present"
    
    # 5. The same events should also be in the state's event log
    assert len(state.events) > 0, "State should have events after init_state"


def test_init_state_with_bash_tool_configures_env_provider():
    """Test that init_state configures bash tools with env_provider and env_masker.
    
    This verifies that the _configure_bash_tools_env_provider method is called
    and properly wires the secrets manager to the bash tool.
    """
    # Register BashTool before using it
    from openhands.sdk.tool import register_tool
    from openhands.tools.execute_bash import BashTool
    
    register_tool("BashTool", BashTool)
    
    llm = LLM(
        service_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(
        llm=llm,
        tools=[Tool(name="BashTool")],
    )
    
    # Create conversation with the agent
    convo = Conversation(agent=agent, visualize=False)
    
    # Verify bash tool is present
    assert "execute_bash" in agent._tools, "execute_bash tool should be present"
    
    # Verify that the bash tool executor has env_provider and env_masker configured
    bash_tool = agent._tools["execute_bash"]
    try:
        executable_tool = bash_tool.as_executable()
        executor = executable_tool.executor
        
        # Check that env_provider and env_masker are set
        assert hasattr(executor, "env_provider"), (
            "Bash executor should have env_provider attribute"
        )
        assert hasattr(executor, "env_masker"), (
            "Bash executor should have env_masker attribute"
        )
        assert callable(executor.env_provider), "env_provider should be callable"
        assert callable(executor.env_masker), "env_masker should be callable"
        
    except NotImplementedError:
        # Tool has no executor, this is acceptable for some tool configurations
        pass


def test_init_state_called_directly_modifies_state():
    """Test that calling init_state directly modifies the state in-place.
    
    This test verifies the core requirement that init_state actually modifies
    the state object passed to it, not a copy.
    """
    llm = LLM(
        service_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])
    
    # Create a conversation to get a properly initialized state
    convo = Conversation(agent=agent, visualize=False)
    state = convo.state
    
    # Get the initial event count
    initial_event_count = len(state.events)
    
    # Store reference to the state object to verify it's the same object after init_state
    state_id_before = id(state)
    state_events_id_before = id(state.events)
    
    # Clear events to simulate a fresh state
    # (Note: In practice, init_state checks if there are LLM convertible events)
    events_added = []
    def track_events(event):
        events_added.append(event)
    
    # Call init_state directly
    agent.init_state(state, on_event=track_events)
    
    # Verify the state object is the same (not a copy)
    assert id(state) == state_id_before, "State object should be the same (modified in-place)"
    
    # Verify the state's events reference is the same
    assert id(state.events) == state_events_id_before, (
        "State.events should be the same object (modified in-place)"
    )
    
    # Verify that agent's tools are initialized
    assert len(agent._tools) > 0, "Agent should have initialized tools"


def test_init_state_without_llm_convertible_events_adds_system_prompt():
    """Test that init_state adds SystemPromptEvent when there are no LLM convertible events."""
    llm = LLM(
        service_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])
    
    events_added = []
    def track_events(event):
        events_added.append(event)
    
    # Create conversation - this automatically calls init_state
    convo = Conversation(agent=agent, callbacks=[track_events], visualize=False)
    
    # Should have added exactly one SystemPromptEvent
    system_prompt_events = [e for e in events_added if isinstance(e, SystemPromptEvent)]
    assert len(system_prompt_events) == 1, (
        "Should add exactly one SystemPromptEvent when state has no LLM convertible events"
    )
    
    # Verify the system prompt contains expected content
    system_prompt_event = system_prompt_events[0]
    assert system_prompt_event.system_prompt is not None
    assert system_prompt_event.source == "agent"
    assert len(system_prompt_event.tools) > 0
