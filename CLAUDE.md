# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenHands Agent SDK enables building software with AI agents. This SDK powers the OpenHands project and allows developers to create custom agents that write code, debug issues, automate tasks, and interact with various tools.

The repository is structured as a **UV workspace** with four main packages:
- `openhands/sdk`: Core agent functionality, LLM integration, conversation management
- `openhands/tools`: Built-in tools (bash, file editing, task tracking, browser automation)
- `openhands/workspace`: Workspace management (local and remote execution environments)
- `openhands/agent_server`: FastAPI-based REST/WebSocket server for remote agent interactions

## Development Commands

### Environment Setup
```bash
# Initial setup (install dependencies + pre-commit hooks)
make build

# Add new dependencies
uv add package-name            # Runtime dependency
uv add --dev package-name      # Development dependency
```

### Code Quality
```bash
# Format code
make format                    # or: uv run ruff format

# Lint and auto-fix
make lint                      # or: uv run ruff check --fix

# Type checking
uv run pyright                 # Runs on pre-commit

# Run all pre-commit hooks
uv run pre-commit run --all-files
uv run pre-commit run --files path/to/file.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run specific test suites
uv run pytest tests/sdk/
uv run pytest tests/tools/
uv run pytest tests/agent_server/
uv run pytest tests/cross/
uv run pytest tests/integration/

# Run with coverage
uv run pytest --cov=openhands --cov-report=html

# Run specific test file or function
uv run pytest tests/sdk/test_conversation.py
uv run pytest tests/sdk/test_conversation.py::test_function_name
```

### Agent Server
```bash
# Build server executable
make build-server

# Validate OpenAPI schema
make test-server-schema
```

### Running Examples
```bash
# Set API key first
export LLM_API_KEY=your_key_here

# Run examples (standalone SDK usage)
uv run python examples/01_standalone_sdk/*.py

# Examples requiring agent server
cd examples/02_remote_agent_server
# Follow README in that directory
```

## Architecture

### Core SDK Architecture

**Agent (`openhands/sdk/agent/`)**: The central orchestrator that coordinates LLMs, tools, and conversation state. Agents can be created via presets (`get_default_agent()` or `get_planning_agent()`) or manually configured with specific tools.

**Conversation (`openhands/sdk/conversation/`)**: Manages interaction flow between users and agents. Key components:
- `Conversation`: Main class for SDK usage
- `LocalConversation`: Runs agent locally in same process
- `RemoteConversation`: Connects to remote agent via WebSocket
- `EventStore`: Persists conversation history
- `StuckDetector`: Detects and handles infinite loops

**LLM Integration (`openhands/sdk/llm/`)**: Unified interface for multiple LLM providers via LiteLLM. Supports function calling, multimodal inputs, and custom routing strategies. `LLMRegistry` manages shared LLM configurations.

**Context Management (`openhands/sdk/context/`)**: Controls agent behavior and memory:
- `AgentContext`: System/user message customization
- `Microagents`: Inject context based on triggers (repo-wide or keyword-based)
- `Condenser`: Manages conversation history truncation (e.g., `LLMSummarizingCondenser` replaces old events with summaries)

**Tools (`openhands/sdk/tool/` and `openhands/tools/`)**: Tools are registered via `register_tool()` and instantiated with `Tool()` specs:
- `BashTool`: Execute bash commands in persistent shell
- `FileEditorTool`: Create/edit files with advanced editing capabilities
- `TaskTrackerTool`: Organize and track development tasks
- `BrowserToolSet`: Web automation (disabled in CLI mode)
- Built-in tools: `ThinkTool` (reasoning) and `FinishTool` (task completion)

**MCP Integration (`openhands/sdk/mcp/`)**: Model Context Protocol support for external tool providers. Default preset includes `mcp-server-fetch` (web fetching) and `repomix` (codebase packing).

**Security (`openhands/sdk/security/`)**: `LLMSecurityAnalyzer` analyzes tool calls for potential risks and can prompt for user confirmation on risky actions.

**Events (`openhands/sdk/event/`)**: All actions and observations are represented as events. `LLMConvertibleEvent` types can be serialized to/from LLM messages.

### Agent Server Architecture

**API Layer (`openhands/agent_server/api.py`)**: FastAPI application with REST endpoints and WebSocket support. Routes are organized by domain:
- `conversation_router`: Create/manage conversations
- `event_router`: Query conversation events
- `bash_router`, `file_router`, `tool_router`: Direct tool access
- `vscode_router`, `desktop_router`: IDE/desktop integration
- `sockets_router`: WebSocket connections for real-time updates

**Services**:
- `conversation_service`: Manages conversation lifecycle
- `vscode_service`, `desktop_service`: Optional IDE/desktop environment management

**Pub/Sub (`pub_sub.py`)**: In-memory event bus for broadcasting conversation updates to WebSocket clients.

**Docker Support**: Dockerfiles in `openhands/agent_server/docker/` for containerized deployment.

### Workspace Management

**Workspace (`openhands/workspace/`)**: Abstracts execution environments. `LocalWorkspace` runs on host, `RemoteWorkspace` connects to remote environments via API.

## Key Patterns and Conventions

### Tool Development
Tools must inherit from `ToolBase` and implement `get_schema()` and `execute()`. Register tools before agent creation:
```python
from openhands.sdk.tool import register_tool
register_tool("MyTool", MyToolClass)
```

### Conversation Flow
1. Create agent with LLM and tools
2. Create conversation with agent
3. Send messages via `conversation.send_message()`
4. Run conversation with `conversation.run()` (blocks until agent awaits user input)
5. Access events via `conversation.events`

### Event-Driven Design
All interactions are events. Tools produce `Action` events (what agent wants to do) and `Observation` events (results). The conversation loop processes events until agent enters "await user input" state.

### UV Workspace Structure
This is a monorepo with inter-package dependencies managed by UV workspace. When modifying dependencies:
- Add to the appropriate package's `pyproject.toml`
- Run `uv sync` to update lockfile
- Workspace sources are defined in root `pyproject.toml` `[tool.uv.sources]`

### Testing Structure
- `tests/sdk/`: Core SDK functionality tests
- `tests/tools/`: Individual tool tests
- `tests/agent_server/`: Server API tests
- `tests/cross/`: Cross-package integration tests
- `tests/integration/`: Full end-to-end tests
- Use `pytest-asyncio` for async tests (asyncio_mode = "auto" in pyproject.toml)

## Important Notes

- Python 3.12+ required
- UV 0.8.13+ required for workspace support
- Pre-commit hooks enforce ruff formatting, linting, pycodestyle, and pyright type checking
- All LLM interactions go through LiteLLM for provider abstraction
- Default preset includes MCP servers: `mcp-server-fetch` and `repomix`
- Browser tools are automatically disabled when `cli_mode=True`
- Security analyzer is enabled by default in the default preset
