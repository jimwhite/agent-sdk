# Agent-SDK API Design - Simplified 1-1 Mapping

## Overview

This document outlines a simplified REST API design that provides strict 1-1 correspondence with the `Conversation` class public methods and properties. This approach ensures clean mapping between HTTP endpoints and SDK functionality.

## Conversation Class Analysis

### Public Methods & Properties
From `openhands/sdk/conversation/conversation.py`:

1. `__init__(agent, callbacks, max_iteration_per_run, visualize)` - Constructor
2. `id` (property) - Get conversation ID
3. `send_message(message: Message)` - Send user message
4. `run()` - Run conversation steps
5. `set_confirmation_mode(enabled: bool)` - Enable/disable confirmation mode
6. `reject_pending_actions(reason: str)` - Reject pending actions
7. `pause()` - Pause conversation execution

### State Access
Via `conversation.state` (ConversationState):
- `events: list[Event]` - List of all events
- `agent_finished: bool` - Whether agent is finished
- `confirmation_mode: bool` - Current confirmation mode
- `agent_waiting_for_confirmation: bool` - Waiting for confirmation
- `agent_paused: bool` - Whether paused
- And other state properties...

## API Endpoint Design

### 1-1 Method Mapping

| Conversation Method | HTTP Method | Endpoint | Description |
|-------------------|-------------|----------|-------------|
| `__init__()` | `POST` | `/conversations` | Create new conversation |
| `id` (property) | `GET` | `/conversations/{id}` | Get conversation info |
| `send_message()` | `POST` | `/conversations/{id}/send_message` | Send message |
| `run()` | `POST` | `/conversations/{id}/run` | Run conversation |
| `set_confirmation_mode()` | `POST` | `/conversations/{id}/set_confirmation_mode` | Set confirmation mode |
| `reject_pending_actions()` | `POST` | `/conversations/{id}/reject_pending_actions` | Reject pending actions |
| `pause()` | `POST` | `/conversations/{id}/pause` | Pause conversation |

### State Access Endpoints

| State Property | HTTP Method | Endpoint | Description |
|---------------|-------------|----------|-------------|
| `state.events` | `GET` | `/conversations/{id}/events` | Get all events |
| `state` (full) | `GET` | `/conversations/{id}/state` | Get full conversation state |

### Management Endpoints

| Operation | HTTP Method | Endpoint | Description |
|-----------|-------------|----------|-------------|
| List all | `GET` | `/conversations` | List all conversations |
| Delete | `DELETE` | `/conversations/{id}` | Delete conversation |
| Health | `GET` | `/alive` | Health check (no auth) |

## Request/Response Models

### Create Conversation Request
```python
class CreateConversationRequest(BaseModel):
    """Maps to Conversation.__init__() parameters"""
    agent_config: AgentConfig
    max_iteration_per_run: int = 500
    visualize: bool = True
    # callbacks handled internally by server

class AgentConfig(BaseModel):
    """Configuration for creating an Agent"""
    llm_config: dict[str, Any]  # From LLM.model_dump()
    tools: list[str] = []  # Tool names to enable
    workdir: str | None = None  # Working directory
```

### Send Message Request
```python
class SendMessageRequest(BaseModel):
    """Maps to Conversation.send_message() parameters"""
    message: Message  # Direct use of SDK Message model
```

### Set Confirmation Mode Request
```python
class SetConfirmationModeRequest(BaseModel):
    """Maps to Conversation.set_confirmation_mode() parameters"""
    enabled: bool
```

### Reject Pending Actions Request
```python
class RejectPendingActionsRequest(BaseModel):
    """Maps to Conversation.reject_pending_actions() parameters"""
    reason: str = "User rejected the action"
```

### Conversation Response
```python
class ConversationResponse(BaseModel):
    """Response model for conversation info"""
    id: str
    agent_config: AgentConfig
    max_iteration_per_run: int
    visualize: bool
    created_at: str
    
    @classmethod
    def from_conversation(cls, conversation: Conversation, agent_config: AgentConfig):
        return cls(
            id=conversation.id,
            agent_config=agent_config,
            max_iteration_per_run=conversation.max_iteration_per_run,
            visualize=conversation._visualizer is not None,
            created_at=datetime.now().isoformat()
        )
```

### State Response
```python
class ConversationStateResponse(BaseModel):
    """Direct mapping from ConversationState.model_dump()"""
    id: str
    events: list[dict[str, Any]]  # Serialized events
    agent_finished: bool
    confirmation_mode: bool
    agent_waiting_for_confirmation: bool
    agent_paused: bool
    activated_knowledge_microagents: list[str]
    
    @classmethod
    def from_state(cls, state: ConversationState):
        return cls(
            id=state.id,
            events=[event.model_dump() for event in state.events],
            agent_finished=state.agent_finished,
            confirmation_mode=state.confirmation_mode,
            agent_waiting_for_confirmation=state.agent_waiting_for_confirmation,
            agent_paused=state.agent_paused,
            activated_knowledge_microagents=state.activated_knowledge_microagents
        )
```

## Directory Structure

```
openhands/server/
├── __init__.py
├── main.py                    # FastAPI app entry point
├── models/
│   ├── __init__.py
│   ├── requests.py           # Request models
│   └── responses.py          # Response models
├── routers/
│   ├── __init__.py
│   └── conversations.py     # All conversation endpoints
├── services/
│   ├── __init__.py
│   └── conversation_manager.py  # Conversation lifecycle management
├── middleware/
│   ├── __init__.py
│   └── auth.py              # Master key authentication
└── dependencies.py          # FastAPI dependencies
```

## API Implementation

### Router Implementation
```python
# openhands/server/routers/conversations.py
from fastapi import APIRouter, HTTPException, Depends
from openhands.sdk import Conversation, Agent, LLM, Message
from openhands.tools import BashTool, FileEditorTool
from ..models.requests import *
from ..models.responses import *
from ..services.conversation_manager import ConversationManager
from ..dependencies import get_conversation_manager

router = APIRouter()

@router.post("/", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Create new conversation - maps to Conversation.__init__()"""
    return await manager.create_conversation(request)

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Get conversation info - maps to conversation.id property"""
    return await manager.get_conversation_info(conversation_id)

@router.post("/{conversation_id}/send_message")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Send message - maps to conversation.send_message()"""
    conversation = await manager.get_conversation(conversation_id)
    conversation.send_message(request.message)
    return {"status": "message_sent"}

@router.post("/{conversation_id}/run")
async def run_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Run conversation - maps to conversation.run()"""
    conversation = await manager.get_conversation(conversation_id)
    conversation.run()
    return {"status": "run_completed"}

@router.post("/{conversation_id}/set_confirmation_mode")
async def set_confirmation_mode(
    conversation_id: str,
    request: SetConfirmationModeRequest,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Set confirmation mode - maps to conversation.set_confirmation_mode()"""
    conversation = await manager.get_conversation(conversation_id)
    conversation.set_confirmation_mode(request.enabled)
    return {"status": "confirmation_mode_set", "enabled": request.enabled}

@router.post("/{conversation_id}/reject_pending_actions")
async def reject_pending_actions(
    conversation_id: str,
    request: RejectPendingActionsRequest,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Reject pending actions - maps to conversation.reject_pending_actions()"""
    conversation = await manager.get_conversation(conversation_id)
    conversation.reject_pending_actions(request.reason)
    return {"status": "actions_rejected", "reason": request.reason}

@router.post("/{conversation_id}/pause")
async def pause_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Pause conversation - maps to conversation.pause()"""
    conversation = await manager.get_conversation(conversation_id)
    conversation.pause()
    return {"status": "paused"}

@router.get("/{conversation_id}/events")
async def get_events(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Get events - maps to conversation.state.events"""
    conversation = await manager.get_conversation(conversation_id)
    return [event.model_dump() for event in conversation.state.events]

@router.get("/{conversation_id}/state", response_model=ConversationStateResponse)
async def get_state(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Get full state - maps to conversation.state"""
    conversation = await manager.get_conversation(conversation_id)
    return ConversationStateResponse.from_state(conversation.state)

@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """List all conversations"""
    return await manager.list_conversations()

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    manager: ConversationManager = Depends(get_conversation_manager)
):
    """Delete conversation"""
    await manager.delete_conversation(conversation_id)
    return {"status": "deleted"}
```

### Conversation Manager Service
```python
# openhands/server/services/conversation_manager.py
from typing import Dict
from openhands.sdk import Conversation, Agent, LLM
from openhands.tools import BashTool, FileEditorTool
from ..models.requests import CreateConversationRequest, AgentConfig
from ..models.responses import ConversationResponse

class ConversationManager:
    def __init__(self):
        self._conversations: Dict[str, Conversation] = {}
        self._agent_configs: Dict[str, AgentConfig] = {}  # Store for response generation
    
    async def create_conversation(self, request: CreateConversationRequest) -> ConversationResponse:
        """Create new conversation from request"""
        # Create LLM from config
        llm = LLM(**request.agent_config.llm_config)
        
        # Create tools
        tools = []
        if "bash" in request.agent_config.tools:
            workdir = request.agent_config.workdir or "/tmp"
            tools.append(BashTool(working_dir=workdir))
        if "file_editor" in request.agent_config.tools:
            tools.append(FileEditorTool())
        
        # Create agent
        agent = Agent(llm=llm, tools=tools)
        
        # Create conversation
        conversation = Conversation(
            agent=agent,
            max_iteration_per_run=request.max_iteration_per_run,
            visualize=request.visualize
        )
        
        # Store conversation and config
        self._conversations[conversation.id] = conversation
        self._agent_configs[conversation.id] = request.agent_config
        
        return ConversationResponse.from_conversation(conversation, request.agent_config)
    
    async def get_conversation(self, conversation_id: str) -> Conversation:
        """Get conversation by ID"""
        if conversation_id not in self._conversations:
            raise HTTPException(404, f"Conversation {conversation_id} not found")
        return self._conversations[conversation_id]
    
    async def get_conversation_info(self, conversation_id: str) -> ConversationResponse:
        """Get conversation info for response"""
        conversation = await self.get_conversation(conversation_id)
        agent_config = self._agent_configs[conversation_id]
        return ConversationResponse.from_conversation(conversation, agent_config)
    
    async def list_conversations(self) -> list[ConversationResponse]:
        """List all conversations"""
        result = []
        for conv_id, conversation in self._conversations.items():
            agent_config = self._agent_configs[conv_id]
            result.append(ConversationResponse.from_conversation(conversation, agent_config))
        return result
    
    async def delete_conversation(self, conversation_id: str):
        """Delete conversation"""
        if conversation_id not in self._conversations:
            raise HTTPException(404, f"Conversation {conversation_id} not found")
        
        del self._conversations[conversation_id]
        del self._agent_configs[conversation_id]
```

### Main Application
```python
# openhands/server/main.py
import os
from fastapi import FastAPI, HTTPException
from .middleware.auth import AuthMiddleware
from .routers import conversations
from .services.conversation_manager import ConversationManager

def create_app() -> FastAPI:
    # Validate master key
    master_key = os.getenv("OPENHANDS_MASTER_KEY")
    if not master_key:
        raise ValueError("OPENHANDS_MASTER_KEY environment variable is required")
    
    app = FastAPI(
        title="Agent-SDK API",
        description="REST API with 1-1 mapping to Conversation class methods",
        version="1.0.0"
    )
    
    # Add authentication middleware
    app.add_middleware(AuthMiddleware, master_key=master_key)
    
    # Include conversation router
    app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
    
    # Health check endpoint (no auth required)
    @app.get("/alive")
    async def health_check():
        return {"status": "alive"}
    
    return app

# Global conversation manager instance
conversation_manager = ConversationManager()

if __name__ == "__main__":
    import uvicorn
    
    app = create_app()
    
    host = os.getenv("OPENHANDS_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("OPENHANDS_SERVER_PORT", "8000"))
    
    uvicorn.run(app, host=host, port=port)
```

### Dependencies
```python
# openhands/server/dependencies.py
from .services.conversation_manager import ConversationManager
from .main import conversation_manager

def get_conversation_manager() -> ConversationManager:
    """FastAPI dependency to get conversation manager"""
    return conversation_manager
```

## OpenAPI Schema Generation

FastAPI will automatically generate OpenAPI schema from the Pydantic models. The schema will include:

1. **Conversation Creation**: `POST /conversations` with `CreateConversationRequest`
2. **Method Endpoints**: Each conversation method as a separate endpoint
3. **State Access**: Endpoints to access conversation state and events
4. **Authentication**: Bearer token authentication on all endpoints except `/alive`

### Example Usage

```bash
# Create conversation
curl -X POST "http://localhost:8000/conversations" \
  -H "Authorization: Bearer your-master-key" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_config": {
      "llm_config": {
        "model": "claude-sonnet-4-20250514",
        "api_key": "your-api-key"
      },
      "tools": ["bash", "file_editor"],
      "workdir": "/tmp/workspace"
    },
    "max_iteration_per_run": 500,
    "visualize": true
  }'

# Send message
curl -X POST "http://localhost:8000/conversations/{id}/send_message" \
  -H "Authorization: Bearer your-master-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "role": "user",
      "content": [{"type": "text", "text": "Hello!"}]
    }
  }'

# Run conversation
curl -X POST "http://localhost:8000/conversations/{id}/run" \
  -H "Authorization: Bearer your-master-key"

# Get events
curl -X GET "http://localhost:8000/conversations/{id}/events" \
  -H "Authorization: Bearer your-master-key"
```

## Benefits of This Approach

1. **Perfect 1-1 Mapping**: Each HTTP endpoint corresponds exactly to a Conversation method
2. **Predictable API**: Developers familiar with the SDK can easily use the API
3. **Automatic Documentation**: OpenAPI schema directly reflects SDK capabilities
4. **Type Safety**: Pydantic models ensure request/response validation
5. **Simplicity**: No complex abstractions or transformations
6. **Maintainability**: Changes to Conversation class can be directly reflected in API

## Configuration

### Environment Variables
- `OPENHANDS_MASTER_KEY` - Required master key for authentication
- `OPENHANDS_SERVER_HOST` - Server host (default: "0.0.0.0")
- `OPENHANDS_SERVER_PORT` - Server port (default: 8000)

This simplified design provides a clean, predictable API that directly exposes the Conversation class functionality via HTTP while maintaining the same method signatures and behavior.