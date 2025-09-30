"""Tests for ACP server implementation."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from openhands.agent_server.acp.server import OpenHandsACPAgent


@pytest.fixture
def mock_conn():
    """Mock ACP connection."""
    conn = MagicMock()
    conn.sessionUpdate = AsyncMock()
    return conn


@pytest.fixture
def temp_persistence_dir():
    """Temporary persistence directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.mark.asyncio
async def test_initialize(mock_conn, temp_persistence_dir):
    """Test initialize method."""
    from acp import InitializeRequest
    from acp.schema import ClientCapabilities

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    request = InitializeRequest(
        protocolVersion=1,
        clientCapabilities=ClientCapabilities(),
    )

    response = await agent.initialize(request)

    assert response.protocolVersion == 1
    assert response.agentCapabilities is not None
    assert hasattr(response.agentCapabilities, "promptCapabilities")


@pytest.mark.asyncio
async def test_authenticate(mock_conn, temp_persistence_dir):
    """Test authenticate method."""
    from acp.schema import AuthenticateRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)
    request = AuthenticateRequest(methodId="test-method-id")

    response = await agent.authenticate(request)

    assert response is not None


@pytest.mark.asyncio
async def test_new_session(mock_conn, temp_persistence_dir):
    """Test newSession method."""
    from acp import NewSessionRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    request = NewSessionRequest(cwd="/tmp", mcpServers=[])

    response = await agent.newSession(request)

    assert response.sessionId is not None
    assert len(response.sessionId) > 0
    assert response.sessionId in agent._sessions


@pytest.mark.asyncio
async def test_prompt_unknown_session(mock_conn, temp_persistence_dir):
    """Test prompt with unknown session."""
    from acp import PromptRequest
    from acp.schema import ContentBlock1

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    request = PromptRequest(
        sessionId="unknown-session",
        prompt=[ContentBlock1(type="text", text="Hello")],
    )

    with pytest.raises(ValueError, match="Unknown session"):
        await agent.prompt(request)
