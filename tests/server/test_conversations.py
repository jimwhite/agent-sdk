"""Tests for conversation endpoints."""

from unittest.mock import MagicMock, patch


def test_list_conversations_empty(client, auth_headers):
    """Test listing conversations when none exist."""
    response = client.get("/conversations", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@patch("openhands.server.services.conversation_manager.Conversation")
@patch("openhands.server.services.conversation_manager.Agent")
@patch("openhands.server.services.conversation_manager.LLM")
def test_create_conversation(
    mock_llm, mock_agent, mock_conversation, client, auth_headers, sample_agent_config
):
    """Test creating a new conversation."""
    # Mock the conversation instance
    mock_conv_instance = MagicMock()
    mock_conv_instance.id = "test-conv-123"
    mock_conv_instance.max_iteration_per_run = 500
    mock_conv_instance._visualizer = True
    mock_conversation.return_value = mock_conv_instance

    # Mock LLM and Agent
    mock_llm.return_value = MagicMock()
    mock_agent.return_value = MagicMock()

    request_data = {
        "agent_config": sample_agent_config,
        "max_iteration_per_run": 500,
        "visualize": True,
    }

    response = client.post("/conversations", json=request_data, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] == "test-conv-123"
    assert data["max_iteration_per_run"] == 500
    assert data["visualize"] is True


def test_get_nonexistent_conversation(client, auth_headers):
    """Test getting a conversation that doesn't exist."""
    response = client.get("/conversations/nonexistent", headers=auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


@patch("openhands.server.services.conversation_manager.Conversation")
@patch("openhands.server.services.conversation_manager.Agent")
@patch("openhands.server.services.conversation_manager.LLM")
def test_conversation_lifecycle(
    mock_llm, mock_agent, mock_conversation, client, auth_headers, sample_agent_config
):
    """Test full conversation lifecycle: create, get, delete."""
    # Mock the conversation instance
    mock_conv_instance = MagicMock()
    mock_conv_instance.id = "test-conv-456"
    mock_conv_instance.max_iteration_per_run = 500
    mock_conv_instance._visualizer = True
    mock_conversation.return_value = mock_conv_instance

    # Mock LLM and Agent
    mock_llm.return_value = MagicMock()
    mock_agent.return_value = MagicMock()

    # Create conversation
    request_data = {
        "agent_config": sample_agent_config,
        "max_iteration_per_run": 500,
        "visualize": True,
    }

    create_response = client.post(
        "/conversations", json=request_data, headers=auth_headers
    )
    assert create_response.status_code == 201
    conv_id = create_response.json()["id"]

    # Get conversation
    get_response = client.get(f"/conversations/{conv_id}", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == conv_id

    # Delete conversation
    delete_response = client.delete(f"/conversations/{conv_id}", headers=auth_headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "deleted"

    # Verify it's gone
    get_response_after_delete = client.get(
        f"/conversations/{conv_id}", headers=auth_headers
    )
    assert get_response_after_delete.status_code == 404


@patch("openhands.server.services.conversation_manager.Conversation")
@patch("openhands.server.services.conversation_manager.Agent")
@patch("openhands.server.services.conversation_manager.LLM")
def test_send_message(
    mock_llm, mock_agent, mock_conversation, client, auth_headers, sample_agent_config
):
    """Test sending a message to a conversation."""
    # Mock the conversation instance
    mock_conv_instance = MagicMock()
    mock_conv_instance.id = "test-conv-789"
    mock_conv_instance.max_iteration_per_run = 500
    mock_conv_instance._visualizer = True
    mock_conversation.return_value = mock_conv_instance

    # Mock LLM and Agent
    mock_llm.return_value = MagicMock()
    mock_agent.return_value = MagicMock()

    # Create conversation first
    request_data = {
        "agent_config": sample_agent_config,
        "max_iteration_per_run": 500,
        "visualize": True,
    }

    create_response = client.post(
        "/conversations", json=request_data, headers=auth_headers
    )
    conv_id = create_response.json()["id"]

    # Send message
    message_data = {
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": "Hello, agent!"}],
        }
    }

    response = client.post(
        f"/conversations/{conv_id}/send_message",
        json=message_data,
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "message_sent"

    # Verify send_message was called on the conversation
    mock_conv_instance.send_message.assert_called_once()


def test_stats_endpoint(client, auth_headers):
    """Test the stats endpoint."""
    response = client.get("/stats", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "server" in data
    assert "conversations" in data
    assert data["server"]["status"] == "running"
