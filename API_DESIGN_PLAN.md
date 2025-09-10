# Agent-SDK API Design Plan

## Overview

This document outlines the design plan for creating a REST API server for the agent-sdk, enabling HTTP-based access to conversation management, LLM interactions, and agent operations.

## Requirements

- **Single executable** server
- **Multi-conversation management** (1 or more conversations)
- **Per-conversation configuration**:
  - Working directory management
  - LLM credentials (changeable mid-conversation)
  - Message sending/receiving
  - Event list access
  - HTTP callbacks for events
  - File copy in/out operations
  - Command execution
  - Secrets and git provider token management
- **Master key authentication** (from environment variable)
- **Automatic OpenAPI schema generation** from Conversation class
- **LLM configuration** via `.model_dump()`

## Current Codebase Analysis

### Key Classes

1. **Conversation** (`openhands/sdk/conversation/conversation.py`)
   - Properties: `id`, `agent`, `state`, `max_iteration_per_run`
   - Methods: `send_message()`, `run()`, `set_confirmation_mode()`, `reject_pending_actions()`, `pause()`
   - Supports callbacks for events and visualization

2. **ConversationState** (`openhands/sdk/conversation/state.py`)
   - Properties: `id`, `events`, `agent_finished`, `confirmation_mode`, `agent_waiting_for_confirmation`, `agent_paused`
   - Thread-safe with locking mechanism
   - Contains list of Event objects

3. **LLM** (`openhands/sdk/llm/llm.py`)
   - Comprehensive configuration options
   - Has `.model_dump()` method for serialization
   - Supports multiple providers and authentication methods

4. **Event System** (`openhands/sdk/event/`)
   - Base Event class with id, timestamp, source
   - LLMConvertibleEvent for LLM message conversion
   - Polymorphic event types

5. **Tools** (`openhands/tools/`)
   - BashTool, FileEditorTool, TaskTrackerTool
   - Standardized tool interfaces

6. **Agent** (`openhands/sdk/agent/base.py`)
   - Abstract base with LLM, tools, and context
   - Methods: `init_state()`, `step()`

## Proposed Architecture

### Directory Structure

```
openhands/server/
├── __init__.py
├── main.py              # FastAPI app entry point
├── models/              # Pydantic models for API
│   ├── __init__.py
│   ├── conversation.py  # API models derived from Conversation
│   ├── requests.py      # Request/response models
│   └── responses.py
├── routers/             # API route handlers
│   ├── __init__.py
│   ├── conversations.py # Conversation CRUD operations
│   ├── events.py        # Event streaming/callbacks
│   ├── files.py         # File operations
│   └── commands.py      # Command execution
├── services/            # Business logic
│   ├── __init__.py
│   ├── conversation_manager.py
│   ├── event_dispatcher.py
│   └── file_manager.py
├── middleware/          # Authentication & middleware
│   ├── __init__.py
│   └── auth.py
└── utils/
    ├── __init__.py
    └── openapi.py       # OpenAPI schema generation
```

## API Endpoints

### Conversation Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/conversations` | Create new conversation |
| `GET` | `/conversations` | List all conversations |
| `GET` | `/conversations/{id}` | Get conversation details |
| `PUT` | `/conversations/{id}/config` | Update LLM config/workdir |
| `DELETE` | `/conversations/{id}` | Delete conversation |

### Messaging & Control

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/conversations/{id}/messages` | Send message to conversation |
| `POST` | `/conversations/{id}/run` | Run conversation step(s) |
| `POST` | `/conversations/{id}/pause` | Pause conversation |
| `POST` | `/conversations/{id}/confirmation` | Set confirmation mode |
| `POST` | `/conversations/{id}/reject` | Reject pending actions |

### Events & Callbacks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/conversations/{id}/events` | Get event list |
| `GET` | `/conversations/{id}/events/stream` | SSE event stream |
| `POST` | `/conversations/{id}/callbacks` | Register HTTP callback |
| `DELETE` | `/conversations/{id}/callbacks/{callback_id}` | Remove HTTP callback |

### File Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/conversations/{id}/files/upload` | Copy file into conversation |
| `GET` | `/conversations/{id}/files/{path:path}` | Download file from conversation |
| `DELETE` | `/conversations/{id}/files/{path:path}` | Delete file from conversation |
| `GET` | `/conversations/{id}/files` | List files in working directory |

### Command Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/conversations/{id}/commands` | Execute command in conversation context |

### Secrets Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `PUT` | `/conversations/{id}/secrets` | Set secrets/tokens |
| `GET` | `/conversations/{id}/secrets` | List secret keys (not values) |
| `DELETE` | `/conversations/{id}/secrets/{key}` | Remove specific secret |

### Health & Info

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/alive` | Health check (no auth required) |
| `GET` | `/openapi.json` | OpenAPI schema |

## Data Models

### Request Models

```python
# Create Conversation Request
class CreateConversationRequest(BaseModel):
    workdir: str | None = None
    llm_config: dict[str, Any]  # From LLM.model_dump()
    tools: list[str] = []  # Tool names to enable
    max_iteration_per_run: int = 500
    visualize: bool = True

# Send Message Request  
class SendMessageRequest(BaseModel):
    message: Message  # Existing SDK Message model

# Update Config Request
class UpdateConfigRequest(BaseModel):
    workdir: str | None = None
    llm_config: dict[str, Any] | None = None
    max_iteration_per_run: int | None = None

# Register Callback Request
class RegisterCallbackRequest(BaseModel):
    url: str
    events: list[str] | None = None  # Event types to filter, None = all

# Execute Command Request
class ExecuteCommandRequest(BaseModel):
    command: str
    timeout: int | None = None

# Set Secrets Request
class SetSecretsRequest(BaseModel):
    secrets: dict[str, str]
```

### Response Models

```python
# Conversation Response
class ConversationResponse(BaseModel):
    id: str
    workdir: str | None
    llm_config: dict[str, Any]
    state: ConversationStateResponse
    max_iteration_per_run: int
    created_at: str
    updated_at: str

# Conversation State Response
class ConversationStateResponse(BaseModel):
    id: str
    agent_finished: bool
    confirmation_mode: bool
    agent_waiting_for_confirmation: bool
    agent_paused: bool
    event_count: int
    activated_knowledge_microagents: list[str]

# Event Response
class EventResponse(BaseModel):
    # Direct serialization from Event.model_dump()
    id: str
    timestamp: str
    source: str
    type: str
    # Additional fields based on event type

# Command Result Response
class CommandResultResponse(BaseModel):
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
```

## Core Services

### 1. ConversationManager

```python
class ConversationManager:
    """Manages conversation lifecycle and state."""
    
    def __init__(self):
        self._conversations: dict[str, Conversation] = {}
        self._workdirs: dict[str, str] = {}
        self._secrets: dict[str, dict[str, str]] = {}
    
    async def create_conversation(self, request: CreateConversationRequest) -> Conversation
    async def get_conversation(self, conversation_id: str) -> Conversation
    async def update_conversation_config(self, conversation_id: str, config: UpdateConfigRequest)
    async def delete_conversation(self, conversation_id: str)
    async def list_conversations(self) -> list[ConversationResponse]
```

### 2. EventDispatcher

```python
class EventDispatcher:
    """Handles event streaming and HTTP callbacks."""
    
    def __init__(self):
        self._callbacks: dict[str, list[CallbackConfig]] = {}
        self._sse_connections: dict[str, list[SSEConnection]] = {}
    
    async def register_callback(self, conversation_id: str, callback: RegisterCallbackRequest)
    async def dispatch_event(self, conversation_id: str, event: Event)
    async def stream_events(self, conversation_id: str) -> AsyncGenerator[str, None]
```

### 3. FileManager

```python
class FileManager:
    """Handles file operations within conversation context."""
    
    async def upload_file(self, conversation_id: str, file: UploadFile, path: str)
    async def download_file(self, conversation_id: str, path: str) -> FileResponse
    async def delete_file(self, conversation_id: str, path: str)
    async def list_files(self, conversation_id: str, path: str = ".") -> list[FileInfo]
```

## Authentication System

### Master Key Authentication

```python
# Environment variable: OPENHANDS_MASTER_KEY
# Middleware checks Authorization: Bearer <master_key> on all endpoints except /alive

class AuthMiddleware:
    def __init__(self, master_key: str):
        self.master_key = master_key
    
    async def __call__(self, request: Request, call_next):
        if request.url.path == "/alive":
            return await call_next(request)
        
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid authorization header")
        
        token = auth_header.split(" ", 1)[1]
        if token != self.master_key:
            raise HTTPException(401, "Invalid master key")
        
        return await call_next(request)
```

## Event System Design

### HTTP Callbacks

- Each conversation can register multiple HTTP callback URLs
- Events are sent as POST requests with JSON payload
- Support for event filtering by type
- Retry logic with exponential backoff
- Callback management (add/remove/list)

### Server-Sent Events (SSE)

- Real-time event streaming via `/conversations/{id}/events/stream`
- Automatic reconnection support
- Event filtering capabilities
- Connection management and cleanup

### Event Serialization

```python
# Use existing Event.model_dump() for JSON serialization
def serialize_event(event: Event) -> dict[str, Any]:
    return event.model_dump()

# HTTP Callback payload
{
    "conversation_id": "uuid",
    "event": {
        "id": "event-uuid",
        "timestamp": "2024-01-01T00:00:00Z",
        "source": "agent",
        "type": "MessageEvent",
        # ... event-specific fields
    }
}
```

## File Operations Design

### Working Directory Management

- Each conversation has an isolated working directory
- Default to temporary directory if not specified
- Support for absolute and relative paths
- Security boundaries to prevent directory traversal

### File Upload/Download

```python
# Upload endpoint
@router.post("/conversations/{conversation_id}/files/upload")
async def upload_file(
    conversation_id: str,
    file: UploadFile,
    path: str = Query(..., description="Target path relative to workdir")
):
    # Save file to conversation's working directory
    # Return file info and path

# Download endpoint  
@router.get("/conversations/{conversation_id}/files/{path:path}")
async def download_file(conversation_id: str, path: str):
    # Return file from conversation's working directory
    # Support for streaming large files
```

## Command Execution Design

### Integration with BashTool

```python
# Execute command using existing BashTool
@router.post("/conversations/{conversation_id}/commands")
async def execute_command(
    conversation_id: str,
    request: ExecuteCommandRequest
):
    conversation = await conversation_manager.get_conversation(conversation_id)
    
    # Use conversation's BashTool if available
    bash_tool = conversation.agent.tools.get("execute_bash")
    if not bash_tool:
        raise HTTPException(400, "BashTool not available in conversation")
    
    # Execute command and return result
    result = await bash_tool.execute(request.command)
    return CommandResultResponse(
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        execution_time=result.execution_time
    )
```

## Secrets Management Design

### Per-Conversation Environment Variables

```python
class SecretsManager:
    """Manages secrets and environment variables per conversation."""
    
    def __init__(self):
        self._secrets: dict[str, dict[str, str]] = {}
    
    def set_secrets(self, conversation_id: str, secrets: dict[str, str]):
        """Set secrets for a conversation."""
        self._secrets[conversation_id] = {
            **self._secrets.get(conversation_id, {}),
            **secrets
        }
    
    def get_env_for_conversation(self, conversation_id: str) -> dict[str, str]:
        """Get environment variables for conversation context."""
        return self._secrets.get(conversation_id, {})
    
    def remove_secret(self, conversation_id: str, key: str):
        """Remove a specific secret."""
        if conversation_id in self._secrets:
            self._secrets[conversation_id].pop(key, None)
```

### Common Git Provider Tokens

Support for standard environment variables:
- `GITHUB_TOKEN`
- `GITLAB_TOKEN`
- `BITBUCKET_TOKEN`
- Custom secrets as needed

## OpenAPI Schema Generation

### Automatic Schema Generation

```python
# FastAPI automatically generates OpenAPI schema from Pydantic models
# Custom schema enhancements:

def customize_openapi_schema(app: FastAPI):
    """Customize OpenAPI schema with additional information."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Agent-SDK API",
        version="1.0.0",
        description="REST API for OpenHands Agent SDK",
        routes=app.routes,
    )
    
    # Add authentication scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "description": "Master key authentication"
        }
    }
    
    # Apply security to all endpoints except /alive
    for path, methods in openapi_schema["paths"].items():
        if path != "/alive":
            for method_info in methods.values():
                method_info["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

### Model Integration

```python
# Use existing SDK models where possible
class ConversationConfigModel(BaseModel):
    """API model that wraps LLM configuration."""
    
    llm_config: dict[str, Any]  # From LLM.model_dump()
    workdir: str | None = None
    max_iteration_per_run: int = 500
    
    @classmethod
    def from_llm(cls, llm: LLM, **kwargs):
        return cls(llm_config=llm.model_dump(), **kwargs)
    
    def to_llm(self) -> LLM:
        return LLM(**self.llm_config)
```

## Implementation Strategy

### Phase 1: Core Infrastructure
1. Set up FastAPI application structure
2. Implement authentication middleware
3. Create basic conversation management
4. Add health check endpoint

### Phase 2: Basic Conversation Operations
1. Conversation CRUD operations
2. Message sending and conversation running
3. Basic event listing
4. LLM configuration management

### Phase 3: Advanced Features
1. HTTP callbacks and SSE streaming
2. File operations
3. Command execution
4. Secrets management

### Phase 4: Polish & Documentation
1. OpenAPI schema customization
2. Error handling and validation
3. Logging and monitoring
4. Performance optimization

## Security Considerations

### Authentication
- Master key validation on all endpoints except `/alive`
- Secure token handling and storage
- Rate limiting considerations

### Isolation
- Per-conversation working directory isolation
- Environment variable scoping
- File system access controls

### Input Validation
- Path traversal prevention
- Command injection protection
- File upload size limits
- Request payload validation

## Error Handling

### Standard HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid master key)
- `404` - Not Found (conversation/resource not found)
- `409` - Conflict (conversation already exists)
- `500` - Internal Server Error

### Error Response Format
```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict[str, Any] | None = None
```

## Configuration

### Environment Variables
- `OPENHANDS_MASTER_KEY` - Required master key for authentication
- `OPENHANDS_SERVER_HOST` - Server host (default: "0.0.0.0")
- `OPENHANDS_SERVER_PORT` - Server port (default: 8000)
- `OPENHANDS_LOG_LEVEL` - Logging level (default: "INFO")
- `OPENHANDS_WORKDIR_BASE` - Base directory for conversation workdirs

### Server Configuration
```python
# main.py
import os
from fastapi import FastAPI
from openhands.server.middleware.auth import AuthMiddleware
from openhands.server.routers import conversations, events, files, commands

def create_app() -> FastAPI:
    master_key = os.getenv("OPENHANDS_MASTER_KEY")
    if not master_key:
        raise ValueError("OPENHANDS_MASTER_KEY environment variable is required")
    
    app = FastAPI(
        title="Agent-SDK API",
        description="REST API for OpenHands Agent SDK",
        version="1.0.0"
    )
    
    # Add authentication middleware
    app.add_middleware(AuthMiddleware, master_key=master_key)
    
    # Include routers
    app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
    app.include_router(events.router, prefix="/conversations", tags=["events"])
    app.include_router(files.router, prefix="/conversations", tags=["files"])
    app.include_router(commands.router, prefix="/conversations", tags=["commands"])
    
    return app

if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    
    host = os.getenv("OPENHANDS_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("OPENHANDS_SERVER_PORT", "8000"))
    
    uvicorn.run(app, host=host, port=port)
```

## Testing Strategy

### Unit Tests
- Service layer testing with mocked dependencies
- Model validation testing
- Authentication middleware testing

### Integration Tests
- End-to-end API testing
- Conversation lifecycle testing
- Event system testing
- File operations testing

### Load Testing
- Concurrent conversation handling
- Event streaming performance
- File upload/download performance

## Deployment Considerations

### Single Executable
- Package as standalone Python application
- Include all dependencies
- Support for different deployment environments

### Resource Management
- Memory usage for conversation storage
- File system cleanup for temporary directories
- Connection management for SSE streams

### Monitoring
- Health check endpoint for load balancers
- Metrics collection for conversation usage
- Logging for debugging and audit trails

## Future Enhancements

### Persistence
- Database storage for conversation state
- File system persistence options
- Conversation recovery after restart

### Scalability
- Multi-instance deployment support
- Shared state management
- Load balancing considerations

### Advanced Features
- Conversation templates
- Batch operations
- Webhook management UI
- Real-time collaboration features

---

This design provides a comprehensive foundation for implementing the agent-sdk API server while leveraging the existing well-structured codebase and maintaining simplicity and clarity in the implementation.