# OpenHands Agent Client Protocol (ACP) Implementation

This module provides Agent Client Protocol (ACP) support for OpenHands, enabling integration with editors like Zed, Vim, and other ACP-capable clients.

## Overview

The ACP implementation uses the [agent-client-protocol](https://github.com/PsiACE/agent-client-protocol-python) Python SDK to provide a clean, standards-compliant interface for editor integration.

## Features

- **Complete ACP baseline methods**:
  - `initialize` - Protocol negotiation and capabilities exchange
  - `authenticate` - Agent authentication (no-op implementation)
  - `session/new` - Create new conversation sessions
  - `session/prompt` - Send prompts to the agent

- **Session management**: Maps ACP sessions to OpenHands conversation IDs
- **Streaming responses**: Real-time updates via `session/update` notifications
- **Tool integration**: Tool calls and results are streamed to the client
- **Error handling**: Comprehensive error handling and reporting

## Usage

### Starting the ACP Server

```bash
# Using the binary (recommended)
./dist/openhands-acp-server --persistence-dir /tmp/acp_data

# Via main CLI
python -m openhands.agent_server --mode acp --persistence-dir /tmp/acp_data

# Direct module execution
python -m openhands.agent_server.acp --persistence-dir /tmp/acp_data
```

### Building the Binary

```bash
# Build the standalone executable
make build-acp-server

# The binary will be created at: ./dist/openhands-acp-server
```

### Editor Integration

The ACP server communicates over stdin/stdout using NDJSON format with JSON-RPC 2.0 messages.

#### Zed Editor Configuration

Add to your Zed `settings.json`:

```json
{
  "agent_servers": {
    "OpenHands": {
      "command": "/path/to/openhands-acp-server",
      "args": [
        "--persistence-dir", "/tmp/openhands_acp"
      ],
      "env": {
        "OPENAI_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

#### Example Protocol Messages

**Initialize:**
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": 1,
    "clientCapabilities": {
      "fs": {"readTextFile": true, "writeTextFile": true},
      "terminal": true
    }
  },
  "id": 1
}
```

**Create Session:**
```json
{
  "jsonrpc": "2.0",
  "method": "session/new",
  "params": {
    "cwd": "/path/to/project",
    "mcpServers": []
  },
  "id": 2
}
```

**Send Prompt:**
```json
{
  "jsonrpc": "2.0",
  "method": "session/prompt",
  "params": {
    "sessionId": "session-uuid",
    "prompt": "Help me write a Python function"
  },
  "id": 3
}
```

### ⚠️ Important: JSON-RPC 2.0 Format Required

The ACP server **requires proper JSON-RPC 2.0 format**. Raw JSON without the JSON-RPC wrapper will be ignored.

❌ **Incorrect (will be ignored):**
```json
{
  "protocolVersion": 1,
  "clientCapabilities": {
    "fs": {"readTextFile": true, "writeTextFile": true},
    "terminal": true
  }
}
```

✅ **Correct:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": 1,
    "clientCapabilities": {
      "fs": {"readTextFile": true, "writeTextFile": true},
      "terminal": true
    }
  }
}
```

## Architecture

The ACP implementation acts as an adapter layer:

1. **Transport Layer**: Uses the `agent-client-protocol` SDK for JSON-RPC communication
2. **Session Management**: Maps ACP sessions to OpenHands conversation IDs
3. **Integration Layer**: Connects to existing OpenHands `ConversationService`
4. **Streaming**: Provides real-time updates via ACP notifications

## Dependencies

- `agent-client-protocol>=0.1.0` - Official ACP Python SDK
- Standard OpenHands dependencies (FastAPI, Pydantic, etc.)

## Testing

Run the ACP-specific tests:

```bash
uv run pytest tests/agent_server/acp/ -v
```

Test with the example client:

```bash
python examples/acp_client_example.py
```

## Future Enhancements

- Session persistence (`session/load` method)
- Rich content support (images, audio)
- Authentication mechanisms
- MCP (Model Context Protocol) integration
- Advanced streaming capabilities