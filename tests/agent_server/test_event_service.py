from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from openhands.agent_server.event_service import EventService
from openhands.agent_server.models import (
    EventPage,
    EventSortOrder,
    StoredConversation,
)
from openhands.sdk import LLM, Agent, Conversation, Message
from openhands.sdk.conversation.state import AgentExecutionStatus, ConversationState
from openhands.sdk.event.llm_convertible import MessageEvent
from openhands.sdk.security.confirmation_policy import NeverConfirm
from openhands.sdk.workspace import LocalWorkspace


@pytest.fixture
def sample_stored_conversation():
    """Create a sample StoredConversation for testing."""
    return StoredConversation(
        id=uuid4(),
        agent=Agent(llm=LLM(model="gpt-4", usage_id="test-llm"), tools=[]),
        workspace=LocalWorkspace(working_dir="workspace/project"),
        confirmation_policy=NeverConfirm(),
        initial_message=None,
        metrics=None,
        created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2025, 1, 1, 12, 30, 0, tzinfo=UTC),
    )


@pytest.fixture
def event_service(sample_stored_conversation):
    """Create an EventService instance for testing."""
    service = EventService(
        stored=sample_stored_conversation,
        conversations_dir=Path("test_conversation_dir"),
        working_dir=Path("test_working_dir"),
    )
    return service


@pytest.fixture
def mock_conversation_with_events():
    """Create a mock conversation with sample events."""
    conversation = MagicMock(spec=Conversation)
    state = MagicMock(spec=ConversationState)

    # Create sample events with different timestamps and kinds
    events = [
        MessageEvent(
            id=f"event{index}", source="user", llm_message=Message(role="user")
        )
        for index in range(1, 6)
    ]

    state.events = events
    state.__enter__ = MagicMock(return_value=state)
    state.__exit__ = MagicMock(return_value=None)
    conversation._state = state

    return conversation


class TestEventServiceSearchEvents:
    """Test cases for EventService.search_events method."""

    @pytest.mark.asyncio
    async def test_search_events_inactive_service(self, event_service):
        """Test that search_events raises ValueError when conversation is not active."""
        event_service._conversation = None

        with pytest.raises(ValueError, match="inactive_service"):
            await event_service.search_events()

    @pytest.mark.asyncio
    async def test_search_events_empty_result(self, event_service):
        """Test search_events with no events."""
        # Mock conversation with empty events
        conversation = MagicMock(spec=Conversation)
        state = MagicMock(spec=ConversationState)
        state.events = []
        state.__enter__ = MagicMock(return_value=state)
        state.__exit__ = MagicMock(return_value=None)
        conversation._state = state

        event_service._conversation = conversation

        result = await event_service.search_events()

        assert isinstance(result, EventPage)
        assert result.items == []
        assert result.next_page_id is None

    @pytest.mark.asyncio
    async def test_search_events_basic(
        self, event_service, mock_conversation_with_events
    ):
        """Test basic search_events functionality."""
        event_service._conversation = mock_conversation_with_events

        result = await event_service.search_events()

        assert len(result.items) == 5
        assert result.next_page_id is None
        # Default sort is TIMESTAMP (ascending), so first event should be earliest
        assert result.items[0].timestamp < result.items[-1].timestamp

    @pytest.mark.asyncio
    async def test_search_events_kind_filter(
        self, event_service, mock_conversation_with_events
    ):
        """Test filtering events by kind."""
        event_service._conversation = mock_conversation_with_events

        # Test filtering by ActionEvent
        result = await event_service.search_events(kind="ActionEvent")
        assert len(result.items) == 0

        # Test filtering by MessageEvent
        result = await event_service.search_events(
            kind="openhands.sdk.event.llm_convertible.message.MessageEvent"
        )
        assert len(result.items) == 5
        for event in result.items:
            assert event.__class__.__name__ == "MessageEvent"

        # Test filtering by non-existent kind
        result = await event_service.search_events(kind="NonExistentEvent")
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_search_events_sorting(
        self, event_service, mock_conversation_with_events
    ):
        """Test sorting events by timestamp."""
        event_service._conversation = mock_conversation_with_events

        # Test TIMESTAMP (ascending) - default
        result = await event_service.search_events(sort_order=EventSortOrder.TIMESTAMP)
        assert len(result.items) == 5
        for i in range(len(result.items) - 1):
            assert result.items[i].timestamp <= result.items[i + 1].timestamp

        # Test TIMESTAMP_DESC (descending)
        result = await event_service.search_events(
            sort_order=EventSortOrder.TIMESTAMP_DESC
        )
        assert len(result.items) == 5
        for i in range(len(result.items) - 1):
            assert result.items[i].timestamp >= result.items[i + 1].timestamp

    @pytest.mark.asyncio
    async def test_search_events_pagination(
        self, event_service, mock_conversation_with_events
    ):
        """Test pagination functionality."""
        event_service._conversation = mock_conversation_with_events

        # Test first page with limit 2
        result = await event_service.search_events(limit=2)
        assert len(result.items) == 2
        assert result.next_page_id is not None

        # Test second page using next_page_id
        result = await event_service.search_events(page_id=result.next_page_id, limit=2)
        assert len(result.items) == 2
        assert result.next_page_id is not None

        # Test third page
        result = await event_service.search_events(page_id=result.next_page_id, limit=2)
        assert len(result.items) == 1  # Only one item left
        assert result.next_page_id is None

    @pytest.mark.asyncio
    async def test_search_events_combined_filter_and_sort(
        self, event_service, mock_conversation_with_events
    ):
        """Test combining kind filtering with sorting."""
        event_service._conversation = mock_conversation_with_events

        # Filter by ActionEvent and sort by TIMESTAMP_DESC
        result = await event_service.search_events(
            kind="openhands.sdk.event.llm_convertible.message.MessageEvent",
            sort_order=EventSortOrder.TIMESTAMP_DESC,
        )

        assert len(result.items) == 5
        for event in result.items:
            assert event.__class__.__name__ == "MessageEvent"
        # Should be sorted by timestamp descending (newest first)
        assert result.items[0].timestamp > result.items[1].timestamp

    @pytest.mark.asyncio
    async def test_search_events_pagination_with_filter(
        self, event_service, mock_conversation_with_events
    ):
        """Test pagination with filtering."""
        event_service._conversation = mock_conversation_with_events

        # Filter by MessageEvent with limit 1
        result = await event_service.search_events(
            kind="openhands.sdk.event.llm_convertible.message.MessageEvent", limit=1
        )
        assert len(result.items) == 1
        assert result.items[0].__class__.__name__ == "MessageEvent"
        assert result.next_page_id is not None

        # Get second page
        result = await event_service.search_events(
            kind="openhands.sdk.event.llm_convertible.message.MessageEvent",
            page_id=result.next_page_id,
            limit=4,
        )
        assert len(result.items) == 4
        assert result.items[0].__class__.__name__ == "MessageEvent"
        assert result.next_page_id is None  # No more MessageEvents

    @pytest.mark.asyncio
    async def test_search_events_invalid_page_id(
        self, event_service, mock_conversation_with_events
    ):
        """Test search_events with invalid page_id."""
        event_service._conversation = mock_conversation_with_events

        # Use a non-existent page_id
        invalid_page_id = "invalid_event_id"
        result = await event_service.search_events(page_id=invalid_page_id)

        # Should return all items since page_id doesn't match any event
        assert len(result.items) == 5
        assert result.next_page_id is None

    @pytest.mark.asyncio
    async def test_search_events_large_limit(
        self, event_service, mock_conversation_with_events
    ):
        """Test search_events with limit larger than available events."""
        event_service._conversation = mock_conversation_with_events

        result = await event_service.search_events(limit=100)

        assert len(result.items) == 5  # All available events
        assert result.next_page_id is None

    @pytest.mark.asyncio
    async def test_search_events_zero_limit(
        self, event_service, mock_conversation_with_events
    ):
        """Test search_events with zero limit."""
        event_service._conversation = mock_conversation_with_events

        result = await event_service.search_events(limit=0)

        assert len(result.items) == 0
        # Should still have next_page_id if there are events available
        assert result.next_page_id is not None

    @pytest.mark.asyncio
    async def test_search_events_exact_pagination_boundary(self, event_service):
        """Test pagination when the number of events exactly matches the limit."""
        # Create exactly 3 events
        conversation = MagicMock(spec=Conversation)
        state = MagicMock(spec=ConversationState)

        events = [
            MessageEvent(
                id=f"event{index}", source="user", llm_message=Message(role="user")
            )
            for index in range(1, 4)
        ]

        state.events = events
        state.__enter__ = MagicMock(return_value=state)
        state.__exit__ = MagicMock(return_value=None)
        conversation._state = state

        event_service._conversation = conversation

        # Request exactly 3 events (same as available)
        result = await event_service.search_events(limit=3)

        assert len(result.items) == 3
        assert result.next_page_id is None  # No more events available


class TestEventServiceCountEvents:
    """Test cases for EventService.count_events method."""

    @pytest.mark.asyncio
    async def test_count_events_inactive_service(self, event_service):
        """Test that count_events raises ValueError when service is inactive."""
        event_service._conversation = None

        with pytest.raises(ValueError, match="inactive_service"):
            await event_service.count_events()

    @pytest.mark.asyncio
    async def test_count_events_empty_result(self, event_service):
        """Test count_events with no events."""
        conversation = MagicMock(spec=Conversation)
        state = MagicMock(spec=ConversationState)
        state.events = []
        state.__enter__ = MagicMock(return_value=state)
        state.__exit__ = MagicMock(return_value=None)
        conversation._state = state

        event_service._conversation = conversation

        result = await event_service.count_events()
        assert result == 0

    @pytest.mark.asyncio
    async def test_count_events_basic(
        self, event_service, mock_conversation_with_events
    ):
        """Test basic count_events functionality."""
        event_service._conversation = mock_conversation_with_events

        result = await event_service.count_events()
        assert result == 5  # Total events in mock_conversation_with_events

    @pytest.mark.asyncio
    async def test_count_events_kind_filter(
        self, event_service, mock_conversation_with_events
    ):
        """Test counting events with kind filter."""
        event_service._conversation = mock_conversation_with_events

        # Count all events
        result = await event_service.count_events()
        assert result == 5

        # Count ActionEvent events (should be 5)
        result = await event_service.count_events(
            kind="openhands.sdk.event.llm_convertible.message.MessageEvent"
        )
        assert result == 5

        # Count non-existent event type (should be 0)
        result = await event_service.count_events(kind="NonExistentEvent")
        assert result == 0


class TestEventServiceSendMessage:
    """Test cases for EventService.send_message method."""

    async def _mock_executor(self, *args):
        """Helper to create a mock coroutine for run_in_executor."""
        return None

    @pytest.mark.asyncio
    async def test_send_message_inactive_service(self, event_service):
        """Test that send_message raises ValueError when service is inactive."""
        event_service._conversation = None
        message = Message(role="user", content=[])

        with pytest.raises(ValueError, match="inactive_service"):
            await event_service.send_message(message)

    @pytest.mark.asyncio
    async def test_send_message_with_run_false_default(self, event_service):
        """Test send_message with default run=True."""
        # Mock conversation and its methods
        conversation = MagicMock()
        state = MagicMock()
        state.agent_status = AgentExecutionStatus.IDLE
        state.__enter__ = MagicMock(return_value=state)
        state.__exit__ = MagicMock(return_value=None)
        conversation.state = state
        conversation.send_message = MagicMock()
        conversation.run = MagicMock()

        event_service._conversation = conversation
        message = Message(role="user", content=[])

        # Mock the event loop and executor
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = self._mock_executor()

            # Call send_message with default run=True
            await event_service.send_message(message)

            # Verify send_message was called via executor
            mock_loop.run_in_executor.assert_any_call(
                None, conversation.send_message, message
            )
            # Verify run was called via executor since run=True and agent is not running
            assert (
                None,
                conversation.run,
            ) not in mock_loop.run_in_executor.call_args_list

    @pytest.mark.asyncio
    async def test_send_message_with_run_false(self, event_service):
        """Test send_message with run=False."""
        # Mock conversation and its methods
        conversation = MagicMock()
        conversation.send_message = MagicMock()
        conversation.run = MagicMock()

        event_service._conversation = conversation
        message = Message(role="user", content=[])

        # Mock the event loop and executor
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = self._mock_executor()

            # Call send_message with run=False
            await event_service.send_message(message, run=False)

            # Verify send_message was called via executor
            mock_loop.run_in_executor.assert_called_once_with(
                None, conversation.send_message, message
            )
            # Verify run was NOT called since run=False
            assert mock_loop.run_in_executor.call_count == 1  # Only send_message call

    @pytest.mark.asyncio
    async def test_send_message_with_run_true_agent_already_running(
        self, event_service
    ):
        """Test send_message with run=True but agent already running."""
        # Mock conversation and its methods
        conversation = MagicMock()
        state = MagicMock()
        state.agent_status = AgentExecutionStatus.RUNNING
        state.__enter__ = MagicMock(return_value=state)
        state.__exit__ = MagicMock(return_value=None)
        conversation.state = state
        conversation.send_message = MagicMock()
        conversation.run = MagicMock()

        event_service._conversation = conversation
        message = Message(role="user", content=[])

        # Mock the event loop and executor
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = self._mock_executor()

            # Call send_message with run=True
            await event_service.send_message(message, run=True)

            # Verify send_message was called via executor
            mock_loop.run_in_executor.assert_called_once_with(
                None, conversation.send_message, message
            )
            # Verify run was NOT called since agent is already running
            assert mock_loop.run_in_executor.call_count == 1  # Only send_message call

    @pytest.mark.asyncio
    async def test_send_message_with_run_true_agent_idle(self, event_service):
        """Test send_message with run=True and agent idle."""
        # Mock conversation and its methods
        conversation = MagicMock()
        state = MagicMock()
        state.agent_status = AgentExecutionStatus.IDLE
        state.__enter__ = MagicMock(return_value=state)
        state.__exit__ = MagicMock(return_value=None)
        conversation.state = state
        conversation.send_message = MagicMock()
        conversation.run = MagicMock()

        event_service._conversation = conversation
        message = Message(role="user", content=[])

        # Mock the event loop and executor
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            mock_loop.run_in_executor.return_value = self._mock_executor()

            # Call send_message with run=True
            await event_service.send_message(message, run=True)

            # Verify send_message was called via executor
            mock_loop.run_in_executor.assert_any_call(
                None, conversation.send_message, message
            )
            # Verify run was called via executor since agent is idle
            mock_loop.run_in_executor.assert_any_call(None, conversation.run)

    @pytest.mark.asyncio
    async def test_send_message_with_different_message_types(self, event_service):
        """Test send_message with different message types."""
        # Mock conversation
        conversation = MagicMock()
        conversation.send_message = MagicMock()
        conversation.run = MagicMock()

        event_service._conversation = conversation

        # Mock the event loop and executor
        with patch("asyncio.get_running_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            # Create a side effect that returns a new coroutine each time
            mock_loop.run_in_executor.side_effect = lambda *args: self._mock_executor()

            # Test with user message (run=False to avoid state checking)
            user_message = Message(role="user", content=[])
            await event_service.send_message(user_message, run=False)
            mock_loop.run_in_executor.assert_any_call(
                None, conversation.send_message, user_message
            )

            # Test with assistant message
            assistant_message = Message(role="assistant", content=[])
            await event_service.send_message(assistant_message, run=False)
            mock_loop.run_in_executor.assert_any_call(
                None, conversation.send_message, assistant_message
            )

            # Test with system message
            system_message = Message(role="system", content=[])
            await event_service.send_message(system_message, run=False)
            mock_loop.run_in_executor.assert_any_call(
                None, conversation.send_message, system_message
            )
