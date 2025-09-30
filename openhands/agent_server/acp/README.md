# Agent Client Protocol (ACP) Support

This module implements the Agent Client Protocol (ACP) for OpenHands, enabling integration with editors like Zed, Vim, and other ACP-compatible tools.

## Overview

The Agent Client Protocol is a standardized way for editors and IDEs to communicate with AI coding agents. This implementation provides:

- JSON-RPC 2.0 transport over stdin/stdout
- All baseline ACP methods (initialize, authenticate, session/new, session/prompt)
- Session management and conversation mapping
- Comprehensive error handling

## Usage

### Starting the ACP Server

```bash
# Start in ACP mode
python -m openhands.agent_server --mode acp

# Or directly
python -m openhands.agent_server.acp
```

### Protocol Flow

1. **Initialize**: Negotiate protocol version and capabilities
2. **Authenticate**: Optional authentication step
3. **Create Session**: Start a new conversation session
4. **Send Prompts**: Send messages to the agent
5. **Cancel**: Cancel ongoing operations (optional)

### Example Messages

#### Initialize
```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "protocolVersion": "1.0.0",
    "clientCapabilities": {
      "fs": {"readTextFile": true, "writeTextFile": false},
      "terminal": false
    }
  },
  "id": 1
}
```

#### Create Session
```json
{
  "jsonrpc": "2.0",
  "method": "session/new",
  "params": {
    "workingDirectory": "/path/to/project"
  },
  "id": 2
}
```

#### Send Prompt
```json
{
  "jsonrpc": "2.0",
  "method": "session/prompt",
  "params": {
    "sessionId": "session-123",
    "prompt": [
      {
        "type": "text",
        "text": "Help me fix this bug in my code"
      }
    ]
  },
  "id": 3
}
```

## Architecture

The ACP implementation consists of:

- **Transport Layer** (`transport.py`): JSON-RPC 2.0 over stdin/stdout
- **Models** (`models.py`): Pydantic models for all ACP messages
- **Server** (`server.py`): Main ACP server with method handlers
- **CLI** (`__main__.py`): Command-line entry point

## Session Management

ACP sessions are mapped to OpenHands conversation IDs:
- Each `session/new` creates a new conversation
- Session IDs are prefixed with "session-" for clarity
- Working directory can be specified per session

## Error Handling

The implementation follows JSON-RPC 2.0 error codes:
- `-32700`: Parse error
- `-32601`: Method not found
- `-32603`: Internal error
- Custom errors for application-specific issues

## Integration with Editors

### Zed Editor

Add to your Zed configuration:

```json
{
  "language_models": {
    "openhands": {
      "provider": "acp",
      "command": ["python", "-m", "openhands.agent_server", "--mode", "acp"]
    }
  }
}
```

### Vim/Neovim

Use with ACP-compatible plugins that support external agent processes.

## Future Enhancements

- Session persistence (`session/load` method)
- Streaming updates (`session/update` notifications)
- Rich content support (images, audio)
- Authentication mechanisms
- MCP integration

## Testing

Run the test suite:

```bash
uv run pytest tests/agent_server/acp/ -v
```

## Debugging

Enable debug mode for detailed logging:

```bash
OPENHANDS_DEBUG=1 python -m openhands.agent_server --mode acp
```