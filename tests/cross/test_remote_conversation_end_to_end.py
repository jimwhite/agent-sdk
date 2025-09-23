"""End-to-end cross tests for RemoteConversation functionality.

These tests verify the complete RemoteConversation workflow similar to
the hello_world_with_agent_server example, but using mocked components
to avoid requiring a real agent server.
"""

import time
import uuid
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from openhands.sdk import LLM, Agent, Conversation
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.sdk.event.llm_convertible import MessageEvent
from openhands.sdk.llm import Message, TextContent
from openhands.sdk.tool import ToolSpec


class TestRemoteConversationEndToEnd:
    """End-to-end tests for RemoteConversation functionality."""

    def setup_method(self):
        """Set up test environment."""
        self.llm = LLM(model="gpt-4", api_key=SecretStr("test-key"))
        self.agent = Agent(llm=self.llm, tools=[])
        self.host = "http://localhost:8000"
        self.conversation_id = str(uuid.uuid4())

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_complete_conversation_workflow(self, mock_httpx_client, mock_ws_client):
        """Test a complete conversation workflow from start to finish."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock conversation creation
        mock_conv_response = Mock()
        mock_conv_response.raise_for_status.return_value = None
        mock_conv_response.json.return_value = {"id": self.conversation_id}

        # Mock events response (initially empty, then with events)
        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {"items": [], "next_page_id": None}

        # Mock message sending
        mock_message_response = Mock()
        mock_message_response.raise_for_status.return_value = None

        # Mock run response
        mock_run_response = Mock()
        mock_run_response.raise_for_status.return_value = None

        # Mock conversation info responses (different states)
        mock_info_idle = Mock()
        mock_info_idle.raise_for_status.return_value = None
        mock_info_idle.json.return_value = {
            "id": self.conversation_id,
            "agent_status": "idle",
            "confirmation_policy": {"kind": "NeverConfirm"},
            "activated_knowledge_microagents": [],
            "agent": self.agent.model_dump(),
        }

        mock_info_running = Mock()
        mock_info_running.raise_for_status.return_value = None
        mock_info_running.json.return_value = {
            "id": self.conversation_id,
            "agent_status": "running",
            "confirmation_policy": {"kind": "NeverConfirm"},
            "activated_knowledge_microagents": [],
            "agent": self.agent.model_dump(),
        }

        mock_info_finished = Mock()
        mock_info_finished.raise_for_status.return_value = None
        mock_info_finished.json.return_value = {
            "id": self.conversation_id,
            "agent_status": "finished",
            "confirmation_policy": {"kind": "NeverConfirm"},
            "activated_knowledge_microagents": [],
            "agent": self.agent.model_dump(),
        }

        # Set up mock responses in order
        mock_client_instance.post.side_effect = [
            mock_conv_response,  # conversation creation
            mock_message_response,  # send_message
            mock_run_response,  # run
        ]
        mock_client_instance.get.side_effect = [
            mock_events_response,  # initial events fetch
            mock_info_idle,  # initial state check
            mock_info_running,  # state during run
            mock_info_finished,  # final state
        ]

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Track events received via callbacks
        received_events = []
        event_tracker = {"last_event_time": time.time()}

        def event_callback(event):
            """Callback to capture events for testing."""
            received_events.append(event)
            event_tracker["last_event_time"] = time.time()

        # Create conversation through factory (like in the example)
        conversation = Conversation(
            agent=self.agent,
            host=self.host,
            callbacks=[event_callback],
            visualize=True,
        )

        # Verify it's a RemoteConversation
        assert isinstance(conversation, RemoteConversation)
        assert str(conversation.id) == self.conversation_id

        # Check initial state
        initial_state = conversation.state
        assert str(initial_state.id) == self.conversation_id
        assert initial_state.agent_status.value == "idle"

        # Send a message (like in the example)
        conversation.send_message(
            "Read the current repo and write 3 facts about the project into FACTS.txt."
        )

        # Verify message was sent
        message_calls = [
            call
            for call in mock_client_instance.post.call_args_list
            if f"/api/conversations/{self.conversation_id}/events/" in str(call)
        ]
        assert len(message_calls) >= 1

        # Run the conversation
        conversation.run()

        # Verify run was called
        run_calls = [
            call
            for call in mock_client_instance.post.call_args_list
            if f"/api/conversations/{self.conversation_id}/run" in str(call)
        ]
        assert len(run_calls) >= 1

        # Check running state
        running_state = conversation.state
        assert running_state.agent_status.value == "running"

        # Check final state
        final_state = conversation.state
        assert final_state.agent_status.value == "finished"

        # Close conversation
        conversation.close()

        # Verify WebSocket client was stopped
        _mock_ws_instance.stop.assert_called_once()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_conversation_with_tools(self, mock_httpx_client, mock_ws_client):
        """Test RemoteConversation with tools (similar to default agent setup)."""
        # Create agent with tools (like get_default_agent)
        tools = [
            ToolSpec(name="BashTool", params={"working_dir": "/tmp"}),
            ToolSpec(name="FileEditorTool"),
        ]
        agent_with_tools = Agent(llm=self.llm, tools=tools)

        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock conversation creation
        mock_conv_response = Mock()
        mock_conv_response.raise_for_status.return_value = None
        mock_conv_response.json.return_value = {"id": self.conversation_id}

        # Mock events response
        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {"items": [], "next_page_id": None}

        mock_client_instance.post.return_value = mock_conv_response
        mock_client_instance.get.return_value = mock_events_response

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation with tools
        conversation = Conversation(
            agent=agent_with_tools,
            host=self.host,
        )

        # Verify conversation was created
        assert isinstance(conversation, RemoteConversation)
        assert str(conversation.id) == self.conversation_id

        # Close conversation
        conversation.close()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_conversation_event_streaming(self, mock_httpx_client, mock_ws_client):
        """Test RemoteConversation event streaming via WebSocket callbacks."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock conversation creation
        mock_conv_response = Mock()
        mock_conv_response.raise_for_status.return_value = None
        mock_conv_response.json.return_value = {"id": self.conversation_id}

        # Mock events response
        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {"items": [], "next_page_id": None}

        mock_client_instance.post.return_value = mock_conv_response
        mock_client_instance.get.return_value = mock_events_response

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Track events received via callbacks
        received_events = []
        event_types = []

        def event_callback(event):
            """Callback to capture events for testing."""
            received_events.append(event)
            event_types.append(type(event).__name__)

        # Create conversation with callback
        conversation = Conversation(
            agent=self.agent,
            host=self.host,
            callbacks=[event_callback],
        )

        # Verify WebSocket client was created with callback
        mock_ws_client.assert_called_once()
        call_args = mock_ws_client.call_args
        # There should be at least our callback (plus any default callbacks)
        assert len(call_args[1]["callbacks"]) >= 1

        # Simulate receiving events through the callback
        # (In real scenario, these would come from WebSocket)
        from datetime import datetime

        test_event = MessageEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            source="agent",
            llm_message=Message(
                role="assistant", content=[TextContent(text="Test response from agent")]
            ),
        )

        # Simulate callback being called
        callback = call_args[1]["callbacks"][0]
        callback(test_event)

        # Verify event was received
        assert len(received_events) == 1
        assert event_types[0] == "MessageEvent"
        assert (
            received_events[0].llm_message.content[0].text == "Test response from agent"
        )

        # Close conversation
        conversation.close()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_conversation_multiple_runs(self, mock_httpx_client, mock_ws_client):
        """Test RemoteConversation with multiple run cycles (like in the example)."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock conversation creation
        mock_conv_response = Mock()
        mock_conv_response.raise_for_status.return_value = None
        mock_conv_response.json.return_value = {"id": self.conversation_id}

        # Mock events response
        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {"items": [], "next_page_id": None}

        # Mock message and run responses
        mock_message_response = Mock()
        mock_message_response.raise_for_status.return_value = None

        mock_run_response = Mock()
        mock_run_response.raise_for_status.return_value = None

        # Mock conversation info responses
        mock_info_response = Mock()
        mock_info_response.raise_for_status.return_value = None
        mock_info_response.json.return_value = {
            "id": self.conversation_id,
            "agent_status": "finished",
            "confirmation_policy": {"kind": "NeverConfirm"},
            "activated_knowledge_microagents": [],
            "agent": self.agent.model_dump(),
        }

        # Set up mock responses for multiple operations
        mock_client_instance.post.side_effect = [
            mock_conv_response,  # conversation creation
            mock_message_response,  # first message
            mock_run_response,  # first run
            mock_message_response,  # second message
            mock_run_response,  # second run
        ]
        mock_client_instance.get.side_effect = [
            mock_events_response,  # initial events fetch
            mock_info_response,  # state check 1
            mock_info_response,  # state check 2
            mock_info_response,  # state check 3
        ]

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation
        conversation = Conversation(
            agent=self.agent,
            host=self.host,
        )

        # First message and run
        conversation.send_message("First task: create a file")
        conversation.run()

        # Check state after first run
        state1 = conversation.state
        assert state1.agent_status.value == "finished"

        # Second message and run (like in the example)
        conversation.send_message("Second task: modify the file")
        conversation.run()

        # Check state after second run
        state2 = conversation.state
        assert state2.agent_status.value == "finished"

        # Verify multiple runs were called
        run_calls = [
            call
            for call in mock_client_instance.post.call_args_list
            if f"/api/conversations/{self.conversation_id}/run" in str(call)
        ]
        assert len(run_calls) == 2

        # Close conversation
        conversation.close()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_conversation_error_recovery(self, mock_httpx_client, mock_ws_client):
        """Test RemoteConversation error handling and recovery."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock conversation creation
        mock_conv_response = Mock()
        mock_conv_response.raise_for_status.return_value = None
        mock_conv_response.json.return_value = {"id": self.conversation_id}

        # Mock events response
        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {"items": [], "next_page_id": None}

        # Mock message response (success)
        mock_message_response = Mock()
        mock_message_response.raise_for_status.return_value = None

        # Mock run response (failure then success)
        mock_run_error = Mock()
        mock_run_error.raise_for_status.side_effect = Exception(
            "Server temporarily unavailable"
        )

        mock_run_success = Mock()
        mock_run_success.raise_for_status.return_value = None

        # Set up mock responses
        mock_client_instance.post.side_effect = [
            mock_conv_response,  # conversation creation
            mock_message_response,  # message
            mock_run_error,  # first run (fails)
            mock_run_success,  # second run (succeeds)
        ]
        mock_client_instance.get.return_value = mock_events_response

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation
        conversation = Conversation(
            agent=self.agent,
            host=self.host,
        )

        # Send message
        conversation.send_message("Test task")

        # First run should fail
        with pytest.raises(Exception, match="Server temporarily unavailable"):
            conversation.run()

        # Second run should succeed
        conversation.run()

        # Verify both run attempts were made
        run_calls = [
            call
            for call in mock_client_instance.post.call_args_list
            if f"/api/conversations/{self.conversation_id}/run" in str(call)
        ]
        assert len(run_calls) == 2

        # Close conversation
        conversation.close()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_conversation_with_existing_id(self, mock_httpx_client, mock_ws_client):
        """Test RemoteConversation resuming an existing conversation."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock events response with existing events
        from datetime import datetime

        existing_event = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "kind": "MessageEvent",
            "source": "user",
            "llm_message": {
                "role": "user",
                "content": [{"type": "text", "text": "Previous message"}],
            },
        }

        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {
            "items": [existing_event],
            "next_page_id": None,
        }

        mock_client_instance.get.return_value = mock_events_response

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation with existing ID
        existing_id = str(uuid.uuid4())
        conversation = Conversation(
            agent=self.agent,
            host=self.host,
            conversation_id=uuid.UUID(existing_id),
        )

        # Verify conversation uses existing ID
        assert str(conversation.id) == existing_id

        # Verify no POST call was made (no new conversation created)
        mock_client_instance.post.assert_not_called()

        # Verify GET call was made to fetch existing events
        mock_client_instance.get.assert_called()

        # Verify events were loaded
        assert len(conversation.state.events) >= 1

        # Close conversation
        conversation.close()
