"""Tests for ACP server."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from openhands.agent_server.acp.server import ACPServer
from openhands.agent_server.models import ConversationInfo


@pytest.fixture
def mock_conversation_service():
    """Mock conversation service."""
    service = Mock()

    # Mock conversation info
    conversation_id = uuid4()
    mock_conversation_info = Mock(spec=ConversationInfo)
    mock_conversation_info.id = conversation_id

    # Mock event service
    mock_event_service = Mock()
    mock_event_service.send_message = AsyncMock()

    # Set up async methods
    service.start_conversation = AsyncMock(return_value=mock_conversation_info)
    service.get_conversation = AsyncMock(return_value=mock_conversation_info)
    service.get_event_service = AsyncMock(return_value=mock_event_service)

    return service


@pytest.fixture
def acp_server(mock_conversation_service):
    """Create ACP server with mocked dependencies."""
    return ACPServer(mock_conversation_service)


def test_handle_initialize(acp_server):
    """Test initialize method."""
    params = {
        "protocolVersion": "1.0.0",
        "clientCapabilities": {
            "fs": {"readTextFile": True, "writeTextFile": False},
            "terminal": True,
        },
    }

    result = acp_server._handle_initialize(params)

    assert result["protocolVersion"] == "1.0.0"
    assert result["serverCapabilities"]["fs"]["readTextFile"] is True
    assert result["serverCapabilities"]["fs"]["writeTextFile"] is True
    assert result["serverCapabilities"]["terminal"] is True
    assert acp_server.initialized is True


def test_handle_initialize_missing_params(acp_server):
    """Test initialize with missing parameters."""
    params = {}

    with pytest.raises(ValueError, match="Invalid initialize request"):
        acp_server._handle_initialize(params)


def test_handle_authenticate(acp_server):
    """Test authenticate method."""
    params = {"token": "test-token"}

    result = acp_server._handle_authenticate(params)

    assert result["success"] is True


def test_handle_session_new(acp_server, mock_conversation_service):
    """Test session/new method."""
    acp_server.initialized = True
    params = {"workingDirectory": "/tmp"}

    result = acp_server._handle_session_new(params)

    assert "sessionId" in result
    session_id = result["sessionId"]
    assert session_id.startswith("session-")
    assert session_id in acp_server.sessions

    # Verify conversation was created
    mock_conversation_service.start_conversation.assert_called_once()


def test_handle_session_prompt(acp_server, mock_conversation_service):
    """Test session/prompt method."""
    acp_server.initialized = True

    # First create a session
    session_params = {"workingDirectory": "/tmp"}
    session_result = acp_server._handle_session_new(session_params)
    session_id = session_result["sessionId"]

    # Now send a prompt
    params = {
        "sessionId": session_id,
        "prompt": [{"type": "text", "text": "Hello, world!"}],
    }

    result = acp_server._handle_session_prompt(params)

    assert "content" in result
    assert len(result["content"]) > 0

    # Verify event service was accessed
    mock_conversation_service.get_event_service.assert_called_once()


def test_handle_session_prompt_unknown_session(acp_server):
    """Test session/prompt with unknown session."""
    acp_server.initialized = True
    params = {
        "sessionId": "unknown-session",
        "prompt": [{"type": "text", "text": "Hello, world!"}],
    }

    with pytest.raises(ValueError, match="Unknown session"):
        acp_server._handle_session_prompt(params)


def test_handle_session_cancel(acp_server):
    """Test session/cancel method."""
    acp_server.initialized = True

    # First create a session
    session_params = {"workingDirectory": "/tmp"}
    session_result = acp_server._handle_session_new(session_params)
    session_id = session_result["sessionId"]

    # Now cancel it
    params = {"sessionId": session_id}

    result = acp_server._handle_session_cancel(params)

    # Should return empty dict for notifications
    assert result == {}


def test_handle_session_cancel_unknown_session(acp_server):
    """Test session/cancel with unknown session."""
    params = {"sessionId": "unknown-session"}

    result = acp_server._handle_session_cancel(params)

    # Should return empty dict for notifications
    assert result == {}
