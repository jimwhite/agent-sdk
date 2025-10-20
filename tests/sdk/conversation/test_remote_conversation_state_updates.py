"""Tests for RemoteConversation state update handling."""

from unittest.mock import patch

from pydantic import SecretStr

from openhands.sdk import RemoteWorkspace
from openhands.sdk.agent import Agent
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.sdk.event.conversation_state import ConversationStateUpdateEvent
from openhands.sdk.llm import LLM

from .conftest import create_mock_http_client


def create_test_agent() -> Agent:
    """Create a test agent for testing."""
    llm = LLM(model="gpt-4o-mini", api_key=SecretStr("test-key"), usage_id="test-llm")
    return Agent(llm=llm, tools=[])


def test_update_state_from_event_with_full_state():
    """Test updating cached state from a full state snapshot."""
    agent = create_test_agent()

    # Mock httpx client
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # Create a full state event
        full_state = {
            "agent_status": "running",
            "confirmation_policy": {"kind": "NeverConfirm"},
            "max_iterations": 100,
        }
        event = ConversationStateUpdateEvent(key="full_state", value=full_state)

        # Update state using the real RemoteState
        conv.state.update_state_from_event(event)

        # Verify all fields were updated
        assert conv.state._cached_state is not None
        assert conv.state._cached_state == full_state
        assert conv.state._cached_state["agent_status"] == "running"
        assert conv.state._cached_state["max_iterations"] == 100


def test_update_state_from_event_with_individual_field():
    """Test updating cached state from an individual field update."""
    agent = create_test_agent()

    # Mock httpx client and its responses
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # Set initial cached state
        conv.state._cached_state = {
            "agent_status": "idle",
            "max_iterations": 50,
        }

        # Create an individual field update event
        event = ConversationStateUpdateEvent(key="agent_status", value="running")

        # Update state using the real RemoteState
        conv.state.update_state_from_event(event)

        # Verify only that field was updated
        assert conv.state._cached_state is not None
        assert conv.state._cached_state["agent_status"] == "running"
        assert conv.state._cached_state["max_iterations"] == 50  # Unchanged


def test_update_state_initializes_cache_if_none():
    """Test that update initializes cache if it doesn't exist."""
    agent = create_test_agent()

    # Mock httpx client and its responses
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # Ensure cache starts as None
        conv.state._cached_state = None

        # Update with individual field when cache is None
        event = ConversationStateUpdateEvent(key="agent_status", value="running")
        conv.state.update_state_from_event(event)

        # Verify cache was initialized
        assert conv.state._cached_state is not None
        assert conv.state._cached_state["agent_status"] == "running"


def test_update_state_from_multiple_events():
    """Test updating state from multiple events."""
    agent = create_test_agent()

    # Mock httpx client and its responses
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # First, full state
        full_state = {
            "agent_status": "idle",
            "max_iterations": 50,
            "stuck_detection": True,
        }
        event1 = ConversationStateUpdateEvent(key="full_state", value=full_state)
        conv.state.update_state_from_event(event1)

        # Then, individual updates
        event2 = ConversationStateUpdateEvent(key="agent_status", value="running")
        conv.state.update_state_from_event(event2)

        event3 = ConversationStateUpdateEvent(key="max_iterations", value=100)
        conv.state.update_state_from_event(event3)

        # Verify final state
        assert conv.state._cached_state is not None
        assert conv.state._cached_state["agent_status"] == "running"
        assert conv.state._cached_state["max_iterations"] == 100
        assert conv.state._cached_state["stuck_detection"] is True


def test_update_state_full_state_overwrites_fields():
    """Test that full_state update properly overwrites existing fields."""
    agent = create_test_agent()

    # Mock httpx client and its responses
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # Set initial cached state
        conv.state._cached_state = {
            "agent_status": "running",
            "max_iterations": 100,
            "old_field": "old_value",
        }

        # Update with full state (without old_field)
        full_state = {
            "agent_status": "idle",
            "max_iterations": 50,
        }
        event = ConversationStateUpdateEvent(key="full_state", value=full_state)
        conv.state.update_state_from_event(event)

        # Verify new fields are set and old field still exists (update, not replace)
        assert conv.state._cached_state is not None
        assert conv.state._cached_state["agent_status"] == "idle"
        assert conv.state._cached_state["max_iterations"] == 50
        assert "old_field" in conv.state._cached_state  # Still there from .update()


def test_update_state_thread_safe():
    """Test that state updates are thread-safe."""
    import threading
    import time

    agent = create_test_agent()

    # Mock httpx client and its responses
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # Set initial cached state
        conv.state._cached_state = {"counter": 0}

        def update_worker(i):
            event = ConversationStateUpdateEvent(key="counter", value=i)
            conv.state.update_state_from_event(event)
            time.sleep(0.001)  # Small delay to encourage race conditions

        # Create multiple threads updating concurrently
        threads = [threading.Thread(target=update_worker, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify state is still valid (should have one of the values)
        assert conv.state._cached_state is not None
        assert "counter" in conv.state._cached_state
        assert 0 <= conv.state._cached_state["counter"] < 10


def test_update_state_preserves_data_types():
    """Test that state updates preserve data types correctly."""
    agent = create_test_agent()

    # Mock httpx client and its responses
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # Update with various data types
        full_state = {
            "string_field": "test",
            "int_field": 42,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"nested": "value"},
        }
        event = ConversationStateUpdateEvent(key="full_state", value=full_state)
        conv.state.update_state_from_event(event)

        # Verify types are preserved
        assert conv.state._cached_state is not None
        assert isinstance(conv.state._cached_state["string_field"], str)
        assert isinstance(conv.state._cached_state["int_field"], int)
        assert isinstance(conv.state._cached_state["bool_field"], bool)
        assert isinstance(conv.state._cached_state["list_field"], list)
        assert isinstance(conv.state._cached_state["dict_field"], dict)


def test_state_update_callback_integration():
    """Test that the state update callback is properly integrated."""
    agent = create_test_agent()

    # Mock httpx client and its responses
    mock_client_instance = create_mock_http_client()

    with (
        patch("httpx.Client", return_value=mock_client_instance),
        patch(
            "openhands.sdk.conversation.impl.remote_conversation"
            ".WebSocketCallbackClient"
        ),
    ):
        # Create real RemoteConversation
        conv = RemoteConversation(
            agent=agent,
            workspace=RemoteWorkspace(working_dir="/tmp", host="http://localhost:3000"),
        )

        # Verify that the state update callback was added to the callbacks
        state_update_callback = conv.state.create_state_update_callback()

        # Test that the callback properly handles ConversationStateUpdateEvent
        event = ConversationStateUpdateEvent(key="agent_status", value="running")

        # Call the callback directly (simulating websocket event)
        state_update_callback(event)

        # Verify the state was updated
        assert conv.state._cached_state is not None
        assert conv.state._cached_state["agent_status"] == "running"
