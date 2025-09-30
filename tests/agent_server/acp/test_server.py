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
    assert response.authMethods is not None
    assert len(response.authMethods) == 1
    assert response.authMethods[0].id == "llm_config"
    assert response.authMethods[0].name == "LLM Configuration"


@pytest.mark.asyncio
async def test_authenticate_llm_config(mock_conn, temp_persistence_dir):
    """Test authenticate method with LLM configuration."""
    from acp.schema import AuthenticateRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # Test LLM configuration authentication
    llm_config = {
        "model": "gpt-4",
        "api_key": "test-api-key",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_output_tokens": 2000,
    }

    request = AuthenticateRequest(methodId="llm_config", **{"_meta": llm_config})
    response = await agent.authenticate(request)

    assert response is not None
    assert agent._llm_config["model"] == "gpt-4"
    assert agent._llm_config["api_key"] == "test-api-key"
    assert agent._llm_config["base_url"] == "https://api.openai.com/v1"
    assert agent._llm_config["temperature"] == 0.7
    assert agent._llm_config["max_output_tokens"] == 2000


@pytest.mark.asyncio
async def test_authenticate_unsupported_method(mock_conn, temp_persistence_dir):
    """Test authenticate method with unsupported method."""
    from acp.schema import AuthenticateRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)
    request = AuthenticateRequest(methodId="unsupported-method")

    response = await agent.authenticate(request)

    assert response is None


@pytest.mark.asyncio
async def test_authenticate_no_config(mock_conn, temp_persistence_dir):
    """Test authenticate method without configuration."""
    from acp.schema import AuthenticateRequest

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)
    request = AuthenticateRequest(methodId="llm_config")

    response = await agent.authenticate(request)

    assert response is not None
    assert len(agent._llm_config) == 0


def test_validate_llm_config(mock_conn, temp_persistence_dir):
    """Test LLM configuration validation."""
    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # Test valid configuration
    config = {
        "model": "gpt-4",
        "api_key": "test-key",
        "temperature": 0.7,
        "unknown_param": "should_be_ignored",
        "max_output_tokens": 2000,
    }

    validated = agent._validate_llm_config(config)

    assert validated["model"] == "gpt-4"
    assert validated["api_key"] == "test-key"
    assert validated["temperature"] == 0.7
    assert validated["max_output_tokens"] == 2000
    assert "unknown_param" not in validated


def test_create_llm_from_config_with_auth(mock_conn, temp_persistence_dir):
    """Test LLM creation with authenticated configuration."""
    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # Set authenticated config
    agent._llm_config = {
        "model": "gpt-4",
        "api_key": "test-key",
        "temperature": 0.5,
    }

    llm = agent._create_llm_from_config()

    assert llm.model == "gpt-4"
    assert llm.api_key is not None
    assert llm.api_key.get_secret_value() == "test-key"
    assert llm.temperature == 0.5
    assert llm.service_id == "acp-agent"


def test_create_llm_from_config_defaults(mock_conn, temp_persistence_dir, monkeypatch):
    """Test LLM creation with default configuration."""
    # Clear environment variables
    monkeypatch.delenv("LITELLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agent = OpenHandsACPAgent(mock_conn, temp_persistence_dir)

    # No authenticated config
    llm = agent._create_llm_from_config()

    assert llm.model == "claude-sonnet-4-20250514"  # Default model
    assert llm.service_id == "acp-agent"


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
