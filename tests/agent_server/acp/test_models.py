"""Tests for ACP models."""

from openhands.agent_server.acp.models import (
    ClientCapabilities,
    FileSystemCapabilities,
    InitializeRequest,
    InitializeResponse,
    NewSessionRequest,
    NewSessionResponse,
    PromptRequest,
    PromptResponse,
    ServerCapabilities,
    TextContent,
)


def test_initialize_request():
    """Test InitializeRequest model."""
    request = InitializeRequest(
        protocolVersion="1.0.0",
        clientCapabilities=ClientCapabilities(
            fs=FileSystemCapabilities(readTextFile=True, writeTextFile=False),
            terminal=True,
        ),
    )
    assert request.protocolVersion == "1.0.0"
    assert request.clientCapabilities.fs.readTextFile is True
    assert request.clientCapabilities.terminal is True


def test_initialize_response():
    """Test InitializeResponse model."""
    response = InitializeResponse(
        protocolVersion="1.0.0",
        serverCapabilities=ServerCapabilities(
            fs=FileSystemCapabilities(readTextFile=True, writeTextFile=True),
            terminal=False,
        ),
    )
    assert response.protocolVersion == "1.0.0"
    assert response.serverCapabilities.fs.readTextFile is True
    assert response.serverCapabilities.fs.writeTextFile is True
    assert response.serverCapabilities.terminal is False


def test_new_session_request():
    """Test NewSessionRequest model."""
    request = NewSessionRequest(workingDirectory="/tmp")
    assert request.workingDirectory == "/tmp"

    # Test with None
    request = NewSessionRequest()
    assert request.workingDirectory is None


def test_new_session_response():
    """Test NewSessionResponse model."""
    response = NewSessionResponse(sessionId="test-session")
    assert response.sessionId == "test-session"


def test_prompt_request():
    """Test PromptRequest model."""
    request = PromptRequest(
        sessionId="test-session",
        prompt=[TextContent(text="Hello, world!")],
    )
    assert request.sessionId == "test-session"
    assert len(request.prompt) == 1
    assert isinstance(request.prompt[0], TextContent)
    assert request.prompt[0].text == "Hello, world!"


def test_prompt_response():
    """Test PromptResponse model."""
    response = PromptResponse(content=[TextContent(text="Hello back!")])
    assert len(response.content) == 1
    content = response.content[0]
    assert content.type == "text"
    if content.type == "text":
        assert content.text == "Hello back!"


def test_text_content():
    """Test TextContent model."""
    content = TextContent(text="Test message")
    assert content.type == "text"
    assert content.text == "Test message"
