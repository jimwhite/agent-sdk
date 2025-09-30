"""Pydantic models for Agent Client Protocol (ACP) messages."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class FileSystemCapabilities(BaseModel):
    """File system capabilities."""

    readTextFile: bool = False
    writeTextFile: bool = False


class ClientCapabilities(BaseModel):
    """Client capabilities for ACP initialization."""

    fs: FileSystemCapabilities = Field(default_factory=FileSystemCapabilities)
    terminal: bool = False


class InitializeRequest(BaseModel):
    """Initialize request for ACP protocol negotiation."""

    protocolVersion: str
    clientCapabilities: ClientCapabilities


class ServerCapabilities(BaseModel):
    """Server capabilities for ACP initialization response."""

    fs: FileSystemCapabilities = Field(default_factory=FileSystemCapabilities)
    terminal: bool = False


class InitializeResponse(BaseModel):
    """Initialize response with server capabilities."""

    protocolVersion: str
    serverCapabilities: ServerCapabilities


class AuthenticateRequest(BaseModel):
    """Authentication request (optional)."""

    token: str | None = None


class AuthenticateResponse(BaseModel):
    """Authentication response."""

    success: bool


class NewSessionRequest(BaseModel):
    """Request to create a new session."""

    workingDirectory: str | None = None


class NewSessionResponse(BaseModel):
    """Response with new session ID."""

    sessionId: str


class TextContent(BaseModel):
    """Text content block."""

    type: Literal["text"] = "text"
    text: str


class ResourceLinkContent(BaseModel):
    """Resource link content block."""

    type: Literal["resource"] = "resource"
    uri: str
    mimeType: str | None = None


ContentBlock = TextContent | ResourceLinkContent


class PromptRequest(BaseModel):
    """Request to send a prompt to the agent."""

    sessionId: str
    prompt: list[ContentBlock]


class PromptResponse(BaseModel):
    """Response from prompt processing."""

    content: list[ContentBlock]


class SessionCancelNotification(BaseModel):
    """Notification to cancel a session."""

    sessionId: str


class SessionUpdateNotification(BaseModel):
    """Notification of session updates."""

    sessionId: str
    content: list[ContentBlock]


class JSONRPCRequest(BaseModel):
    """JSON-RPC 2.0 request message."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] | None = None
    id: int | str | None = None


class JSONRPCResponse(BaseModel):
    """JSON-RPC 2.0 response message."""

    jsonrpc: Literal["2.0"] = "2.0"
    result: dict[str, Any] | None = None
    id: int | str | None = None


class JSONRPCError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: dict[str, Any] | None = None


class JSONRPCErrorResponse(BaseModel):
    """JSON-RPC 2.0 error response message."""

    jsonrpc: Literal["2.0"] = "2.0"
    error: JSONRPCError
    id: int | str | None = None


class JSONRPCNotification(BaseModel):
    """JSON-RPC 2.0 notification message."""

    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] | None = None
