"""Tests for state persistence refactoring in agent.py.

This test verifies that events are properly added to state.events directly in agent.py
rather than relying on the callback mechanism for state persistence.
"""

from pydantic import SecretStr

from openhands.sdk.agent.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.event import SystemPromptEvent
from openhands.sdk.io.memory import InMemoryFileStore
from openhands.sdk.llm import LLM


def test_state_persistence_works_without_callback():
    """Test that state persistence works even with empty callback.

    This is the key test for the refactoring: events should be added to state.events
    directly by agent.py, not by the callback.
    """
    llm = LLM(model="gpt-4o-mini", api_key=SecretStr("test-key"), service_id="test-llm")
    agent = Agent(llm=llm, tools=[])

    # Create conversation with empty callback (simulating the refactored behavior)
    empty_callback_called = []

    def empty_callback(event):
        # This simulates the new _default_callback that doesn't persist to state
        empty_callback_called.append(event.id)
        # Importantly, this callback does NOT add to state.events

    fs = InMemoryFileStore()
    conversation = Conversation(
        agent=agent, persist_filestore=fs, callbacks=[empty_callback]
    )

    # Verify that events are still added to state.events
    # even though the callback doesn't add them
    assert len(conversation.state.events) >= 1
    assert isinstance(conversation.state.events[0], SystemPromptEvent)

    # Verify callback was called but didn't handle persistence
    assert len(empty_callback_called) >= 1
    assert conversation.state.events[0].id in empty_callback_called

    # This proves that agent.py is now responsible for state persistence,
    # not the callback


def test_callback_behavior_after_refactoring():
    """Test that the refactored callback behavior works correctly.

    After refactoring, the default callback should be empty (not persist to state),
    but state persistence should still work because agent.py handles it directly.
    """
    llm = LLM(model="gpt-4o-mini", api_key=SecretStr("test-key"), service_id="test-llm")
    agent = Agent(llm=llm, tools=[])

    # Create conversation with no callbacks (relies on default empty callback)
    fs = InMemoryFileStore()
    conversation = Conversation(
        agent=agent,
        persist_filestore=fs,
        callbacks=[],  # No custom callbacks, will use default empty callback
    )

    # Verify that events are still added to state.events
    # This proves the refactoring worked: state persistence happens in agent.py,
    # not in the callback
    assert len(conversation.state.events) >= 1
    assert isinstance(conversation.state.events[0], SystemPromptEvent)

    # The fact that this works with an empty callback proves that
    # agent.py is now responsible for state persistence
