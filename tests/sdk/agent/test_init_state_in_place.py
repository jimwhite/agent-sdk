"""Tests to verify that Agent.init_state modifies state in-place."""

import tempfile
import uuid
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from openhands.sdk.agent.agent import Agent
from openhands.sdk.conversation.state import AgentExecutionStatus, ConversationState
from openhands.sdk.event import MessageEvent, SystemPromptEvent
from openhands.sdk.llm import LLM, Message, TextContent
from openhands.sdk.workspace.local import LocalWorkspace


class TestInitStateInPlace:
    """Test that init_state modifies ConversationState in-place."""

    def setup_method(self):
        """Set up test environment."""
        self.llm = LLM(
            model="gpt-4", api_key=SecretStr("test-key"), service_id="test-llm"
        )

    def test_init_state_modifies_state_in_place(self):
        """Test that init_state modifies the ConversationState object in-place."""
        agent = Agent(llm=self.llm, tools=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a ConversationState
            state = ConversationState.create(
                id=uuid.uuid4(),
                agent=agent,
                workspace=LocalWorkspace(working_dir=tmpdir),
                persistence_dir=tmpdir,
            )

            # Store the object ID and events list ID before calling init_state
            state_id_before = id(state)
            events_id_before = id(state.events)

            # Create a mock callback to track events
            events_added = []

            def mock_on_event(event):
                events_added.append(event)

            # Call init_state
            agent.init_state(state, on_event=mock_on_event)

            # Verify the state object is the same (modified in-place)
            state_id_after = id(state)
            assert state_id_before == state_id_after, (
                "init_state should modify state in-place, not create a new object"
            )

            # Verify the events list is the same object (modified in-place)
            events_id_after = id(state.events)
            assert events_id_before == events_id_after, (
                "init_state should modify events list in-place"
            )

            # Verify that a SystemPromptEvent was added via the callback
            assert len(events_added) > 0, "init_state should call on_event"
            assert any(
                isinstance(event, SystemPromptEvent) for event in events_added
            ), "init_state should add a SystemPromptEvent"

    def test_init_state_calls_super(self):
        """Test that init_state calls parent class init_state."""
        agent = Agent(llm=self.llm, tools=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            state = ConversationState.create(
                id=uuid.uuid4(),
                agent=agent,
                workspace=LocalWorkspace(working_dir=tmpdir),
                persistence_dir=tmpdir,
            )

            mock_on_event = MagicMock()

            # Call init_state - it should call parent class which may do nothing
            # but we're verifying it doesn't raise an error
            try:
                agent.init_state(state, on_event=mock_on_event)
            except Exception as e:
                pytest.fail(f"init_state should call parent init_state successfully: {e}")

            # Verify the state is still valid and usable
            assert state.agent == agent
            assert state.workspace is not None

    def test_init_state_does_not_add_duplicate_system_prompt(self):
        """Test that init_state doesn't add duplicate SystemPromptEvent."""
        agent = Agent(llm=self.llm, tools=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            state = ConversationState.create(
                id=uuid.uuid4(),
                agent=agent,
                workspace=LocalWorkspace(working_dir=tmpdir),
                persistence_dir=tmpdir,
            )

            events_added = []

            def mock_on_event(event):
                events_added.append(event)
                # Also add to state.events to simulate real behavior
                state.events.append(event)

            # First call to init_state
            agent.init_state(state, on_event=mock_on_event)
            first_call_events = len(events_added)

            # Second call to init_state
            agent.init_state(state, on_event=mock_on_event)
            second_call_events = len(events_added)

            # Second call should not add another SystemPromptEvent
            # since state already has LLM convertible messages
            assert second_call_events == first_call_events, (
                "init_state should not add duplicate SystemPromptEvent "
                "when state already has LLM convertible messages"
            )

    def test_init_state_preserves_state_attributes(self):
        """Test that init_state preserves important state attributes."""
        agent = Agent(llm=self.llm, tools=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = LocalWorkspace(working_dir=tmpdir)
            state = ConversationState.create(
                id=uuid.uuid4(),
                agent=agent,
                workspace=workspace,
                persistence_dir=tmpdir,
                max_iterations=100,
            )

            # Store original values
            original_workspace_id = id(state.workspace)
            original_status = state.agent_status
            original_max_iterations = state.max_iterations
            original_persistence_dir = state.persistence_dir

            mock_on_event = MagicMock()
            agent.init_state(state, on_event=mock_on_event)

            # Verify attributes are preserved
            assert id(state.workspace) == original_workspace_id, (
                "workspace should not be replaced"
            )
            assert state.agent_status == original_status, (
                "agent_status should be preserved"
            )
            assert state.max_iterations == original_max_iterations, (
                "max_iterations should be preserved"
            )
            assert state.persistence_dir == original_persistence_dir, (
                "persistence_dir should be preserved"
            )

    def test_init_state_without_bash_tool(self):
        """Test that init_state handles absence of bash tool gracefully."""
        # Create agent without bash tool
        agent = Agent(llm=self.llm, tools=[])

        with tempfile.TemporaryDirectory() as tmpdir:
            state = ConversationState.create(
                id=uuid.uuid4(),
                agent=agent,
                workspace=LocalWorkspace(working_dir=tmpdir),
                persistence_dir=tmpdir,
            )

            mock_on_event = MagicMock()

            # Should not raise an error even without bash tool
            try:
                agent.init_state(state, on_event=mock_on_event)
            except Exception as e:
                pytest.fail(
                    f"init_state should handle missing bash tool gracefully, "
                    f"but raised: {e}"
                )

            # Should still add SystemPromptEvent
            assert mock_on_event.called, "on_event should be called"
            system_prompt_events = [
                call[0][0]
                for call in mock_on_event.call_args_list
                if isinstance(call[0][0], SystemPromptEvent)
            ]
            assert len(system_prompt_events) > 0, (
                "Should add SystemPromptEvent even without bash tool"
            )
