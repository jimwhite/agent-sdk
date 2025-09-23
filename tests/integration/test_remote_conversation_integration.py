"""Integration tests for RemoteConversation with mock agent server."""

import uuid
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from openhands.sdk import Agent, Conversation
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.sdk.llm import LLM, Message, TextContent


class TestRemoteConversationIntegration:
    """Integration tests for RemoteConversation functionality."""

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
    def test_remote_conversation_full_workflow(self, mock_httpx_client, mock_ws_client):
        """Test a complete RemoteConversation workflow from creation to completion."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock conversation creation
        mock_conv_response = Mock()
        mock_conv_response.raise_for_status.return_value = None
        mock_conv_response.json.return_value = {"id": self.conversation_id}

        # Mock events response (initially empty)
        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {"items": [], "next_page_id": None}

        # Mock run response
        mock_run_response = Mock()
        mock_run_response.raise_for_status.return_value = None

        # Mock conversation info response
        mock_info_response = Mock()
        mock_info_response.raise_for_status.return_value = None
        mock_info_response.json.return_value = {
            "id": self.conversation_id,
            "agent_status": "idle",
            "confirmation_policy": {"kind": "NeverConfirm"},
            "activated_knowledge_microagents": [],
            "agent": self.agent.model_dump(),
        }

        # Set up mock responses in order
        mock_client_instance.post.side_effect = [
            mock_conv_response,  # conversation creation
            Mock(raise_for_status=Mock()),  # send_message
            mock_run_response,  # run
        ]
        mock_client_instance.get.side_effect = [
            mock_events_response,  # initial events fetch
            mock_info_response,  # conversation info
        ]

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation
        conversation = RemoteConversation(agent=self.agent, host=self.host)

        # Verify conversation was created
        assert str(conversation.id) == self.conversation_id
        assert isinstance(conversation, RemoteConversation)

        # Send a message
        conversation.send_message("Hello, agent!")

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

        # Check state
        state = conversation.state
        assert str(state.id) == self.conversation_id
        assert state.agent_status.value == "idle"

        # Close conversation
        conversation.close()

        # Verify WebSocket client was stopped
        _mock_ws_instance.stop.assert_called_once()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_remote_conversation_with_callbacks(
        self, mock_httpx_client, mock_ws_client
    ):
        """Test RemoteConversation with event callbacks."""
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

        # Create callback to track events
        received_events = []

        def event_callback(event):
            received_events.append(event)

        # Create conversation with callback
        conversation = RemoteConversation(
            agent=self.agent, host=self.host, callbacks=[event_callback]
        )

        # Verify WebSocket client was created with callback
        mock_ws_client.assert_called_once()
        call_args = mock_ws_client.call_args
        # There should be at least our callback (plus any default callbacks)
        assert len(call_args[1]["callbacks"]) >= 1

        # Verify conversation was created
        assert str(conversation.id) == self.conversation_id

        # Close conversation
        conversation.close()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_remote_conversation_error_handling(
        self, mock_httpx_client, mock_ws_client
    ):
        """Test RemoteConversation error handling."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock conversation creation failure
        mock_conv_response = Mock()
        mock_conv_response.raise_for_status.side_effect = Exception("Server error")
        mock_client_instance.post.return_value = mock_conv_response

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Creating conversation should raise an exception
        with pytest.raises(Exception, match="Server error"):
            RemoteConversation(agent=self.agent, host=self.host)

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_remote_conversation_existing_conversation_id(
        self, mock_httpx_client, mock_ws_client
    ):
        """Test RemoteConversation with existing conversation ID."""
        # Mock HTTP client
        mock_client_instance = mock_httpx_client.return_value

        # Mock events response
        mock_events_response = Mock()
        mock_events_response.raise_for_status.return_value = None
        mock_events_response.json.return_value = {"items": [], "next_page_id": None}

        mock_client_instance.get.return_value = mock_events_response

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation with existing ID
        existing_id = str(uuid.uuid4())
        conversation = RemoteConversation(
            agent=self.agent, host=self.host, conversation_id=uuid.UUID(existing_id)
        )

        # Verify conversation uses existing ID
        assert str(conversation.id) == existing_id

        # Verify no POST call was made (no new conversation created)
        mock_client_instance.post.assert_not_called()

        # Verify GET call was made to fetch events
        mock_client_instance.get.assert_called()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_remote_conversation_factory_integration(
        self, mock_httpx_client, mock_ws_client
    ):
        """Test RemoteConversation creation through Conversation factory."""
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

        # Create conversation through factory
        conversation = Conversation(agent=self.agent, host=self.host)

        # Verify it's a RemoteConversation
        assert isinstance(conversation, RemoteConversation)
        assert str(conversation.id) == self.conversation_id

        # Close conversation
        conversation.close()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_remote_conversation_message_types(self, mock_httpx_client, mock_ws_client):
        """Test RemoteConversation with different message types."""
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

        # Mock message sending
        mock_message_response = Mock()
        mock_message_response.raise_for_status.return_value = None

        mock_client_instance.post.side_effect = [
            mock_conv_response,  # conversation creation
            mock_message_response,  # string message
            mock_message_response,  # Message object
        ]
        mock_client_instance.get.return_value = mock_events_response

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation
        conversation = RemoteConversation(agent=self.agent, host=self.host)

        # Send string message
        conversation.send_message("Hello, world!")

        # Send Message object
        message = Message(
            role="user", content=[TextContent(text="Hello from message object!")]
        )
        conversation.send_message(message)

        # Verify both messages were sent
        message_calls = [
            call
            for call in mock_client_instance.post.call_args_list
            if f"/api/conversations/{self.conversation_id}/events/" in str(call)
        ]
        assert len(message_calls) == 2

        # Close conversation
        conversation.close()

    @patch(
        "openhands.sdk.conversation.impl.remote_conversation.WebSocketCallbackClient"
    )
    @patch("httpx.Client")
    def test_remote_conversation_state_management(
        self, mock_httpx_client, mock_ws_client
    ):
        """Test RemoteConversation state management."""
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

        # Mock conversation info response
        mock_info_response = Mock()
        mock_info_response.raise_for_status.return_value = None
        mock_info_response.json.return_value = {
            "id": self.conversation_id,
            "agent_status": "running",
            "confirmation_policy": {"kind": "AlwaysConfirm"},
            "activated_knowledge_microagents": ["test_microagent"],
            "agent": self.agent.model_dump(),
        }

        mock_client_instance.post.return_value = mock_conv_response
        mock_client_instance.get.side_effect = [
            mock_events_response,  # initial events fetch
            mock_info_response,  # conversation info 1
            mock_info_response,  # conversation info 2
            mock_info_response,  # conversation info 3
        ]

        # Mock WebSocket client
        _mock_ws_instance = mock_ws_client.return_value

        # Create conversation
        conversation = RemoteConversation(agent=self.agent, host=self.host)

        # Access state properties
        state = conversation.state
        assert str(state.id) == self.conversation_id
        assert state.agent_status.value == "running"
        assert len(state.activated_knowledge_microagents) == 1
        assert "test_microagent" in state.activated_knowledge_microagents

        # Close conversation
        conversation.close()
