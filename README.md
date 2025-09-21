# OpenHands Agent SDK

A clean, modular SDK for building AI agents with OpenHands. This project represents a complete architectural refactor from OpenHands V0, emphasizing simplicity, maintainability, and developer experience.

## Project Overview

The OpenHands Agent SDK provides a streamlined framework for creating AI agents that can interact with tools, manage conversations, and integrate with various LLM providers.

## Repository Structure

```plain
agent-sdk/
├── Makefile                            # Build and development commands
├── pyproject.toml                      # Workspace configuration
├── uv.lock                             # Dependency lock file
├── examples/                           # Usage examples
│   ├── 01_hello_world.py               # Basic agent setup (default agent preset)
│   ├── 02_custom_tools.py              # Custom tool implementation with explicit executor
│   ├── 03_activate_microagent.py       # Microagent usage
│   ├── 04_confirmation_mode_example.py # Interactive confirmation mode
│   ├── 05_use_llm_registry.py          # LLM registry usage
│   ├── 06_interactive_terminal_w_reasoning.py # Terminal interaction with reasoning models
│   ├── 07_mcp_integration.py           # MCP integration
│   ├── 08_mcp_with_oauth.py            # MCP integration with OAuth
│   ├── 09_pause_example.py             # Pause and resume agent execution
│   ├── 10_persistence.py               # Conversation persistence
│   ├── 11_async.py                     # Async agent usage
│   ├── 12_custom_secrets.py            # Custom secrets management
│   ├── 13_get_llm_metrics.py           # LLM metrics and monitoring
│   ├── 14_context_condenser.py         # Context condensation
│   ├── 15_browser_use.py               # Browser automation tools
│   ├── 16_llm_security_analyzer.py     # LLM security analysis
│   └── 17_image_input.py               # Image input example
├── openhands/              # Main SDK packages
│   ├── sdk/                # Core SDK functionality
│   │   ├── agent/          # Agent implementations
│   │   ├── context/        # Context management system
│   │   ├── conversation/   # Conversation management
│   │   ├── event/          # Event system
│   │   ├── io/             # I/O abstractions
│   │   ├── llm/            # LLM integration layer
│   │   ├── mcp/            # Model Context Protocol integration
│   │   ├── tool/           # Tool system
│   │   ├── utils/          # Core utilities
│   │   ├── logger.py       # Logging configuration
│   │   └── pyproject.toml  # SDK package configuration
│   └── tools/              # Runtime tool implementations
│       ├── execute_bash/   # Bash execution tool
│       ├── str_replace_editor/  # File editing tool
│       ├── task_tracker/   # Task tracking tool
│       ├── browser_use/    # Browser automation tools
│       ├── utils/          # Tool utilities
│       └── pyproject.toml  # Tools package configuration
└── tests/                  # Test suites
    ├── cross/              # Cross-package tests
    ├── fixtures/           # Test fixtures and data
    ├── sdk/                # SDK unit tests
    └── tools/              # Tools unit tests
```

## Installation & Quickstart

### Prerequisites

- Python 3.12+
- `uv` package manager (version 0.8.13+)

### Setup

```bash
# Clone the repository
git clone https://github.com/All-Hands-AI/agent-sdk.git
cd agent-sdk

# Install dependencies and setup development environment
make build

# Verify installation
uv run python examples/01_hello_world.py
```

### Hello World Example

```python
import os
from pydantic import SecretStr
from openhands.sdk import LLM, Conversation
from openhands.sdk.preset.default import get_default_agent

# Configure LLM
api_key = os.getenv("LITELLM_API_KEY")
assert api_key is not None, "LITELLM_API_KEY environment variable is not set."
llm = LLM(
    model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
    base_url="https://llm-proxy.eval.all-hands.dev",
    api_key=SecretStr(api_key),
)

# Create a default agent (bash + editor + task tracker, MCP integrations)
agent = get_default_agent(llm=llm, working_dir=os.getcwd(), cli_mode=True)
conversation = Conversation(agent=agent)

# Ask the agent to write facts about this repo, then delete the file
conversation.send_message(
    "Read the current repo and write 3 facts about the project into FACTS.txt."
)
conversation.run()

conversation.send_message("Great! Now delete that file.")
conversation.run()
```

## Core Concepts

### Agents

Agents are the central orchestrators that coordinate between LLMs and tools:

```python
from openhands.sdk import Agent
from openhands.tools.execute_bash import BashTool
from openhands.tools.str_replace_editor import FileEditorTool

# Explicit minimal toolset (bash + editor)
tools = [
    BashTool.create(working_dir=os.getcwd()),
    FileEditorTool.create(),
]

agent = Agent(
    llm=llm,
    tools=tools,
    # Optional: custom context, microagents, etc.
)
```

### LLM Integration

The SDK supports multiple LLM providers through a unified interface:

```python
from openhands.sdk import LLM, LLMRegistry
from pydantic import SecretStr

# Direct LLM configuration
llm = LLM(
    model="gpt-4o-mini",
    api_key=SecretStr("your-api-key"),
    base_url="https://api.openai.com/v1"
)

# Using LLM registry for shared configurations
registry = LLMRegistry()
registry.add("default", llm)
llm = registry.get("default")
```

### Tools

Tools provide agents with capabilities to interact with the environment.

#### Simplified Pattern (Recommended)

Use the preset to get a production-ready default toolset (bash + editor + task tracker + curated MCP tools):

```python
from openhands.sdk.preset.default import get_default_tools

tools = get_default_tools(working_dir=os.getcwd())
```

Or construct the basic tools yourself:

```python
from openhands.sdk import TextContent, ImageContent
from openhands.tools.execute_bash import BashTool
from openhands.tools.str_replace_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool

tools = [
    BashTool.create(working_dir=os.getcwd()),
    FileEditorTool.create(),
    TaskTrackerTool.create(save_dir=os.getcwd()),
]
```

#### Advanced Pattern (For explicitly maintained tool executor)

We explicitly define a `BashExecutor` in this example and reuse it for custom tools:

```python
import os, shlex
from collections.abc import Sequence
from pydantic import Field
from openhands.sdk import TextContent, ImageContent
from openhands.tools.execute_bash import (
    BashExecutor,
    ExecuteBashAction,
    execute_bash_tool,
)

# Explicit executor creation for reuse or customization
bash_executor = BashExecutor(working_dir=os.getcwd())
bash_tool = execute_bash_tool.set_executor(executor=bash_executor)
```

And we can later re-use this bash terminal instance to define a custom tool:

```python
import os, shlex
from collections.abc import Sequence
from pydantic import Field
from openhands.sdk import TextContent, ImageContent
from openhands.sdk.tool import ActionBase, ObservationBase, ToolExecutor
from openhands.tools.execute_bash import BashExecutor, ExecuteBashAction

class GrepAction(ActionBase):
    pattern: str = Field(description="Regex to search for")
    path: str = Field(
        default=".", description="Directory to search (absolute or relative)"
    )
    include: str | None = Field(
        default=None, description="Optional glob to filter files (e.g. '*.py')"
    )


class GrepObservation(ObservationBase):
    output: str = Field(default='')

    @property
    def agent_observation(self) -> Sequence[TextContent | ImageContent]:
        return [TextContent(text=self.output)]

# --- Executor ---
class GrepExecutor(ToolExecutor[GrepAction, GrepObservation]):
    def __init__(self, bash: BashExecutor):
        self.bash = bash

    def __call__(self, action: GrepAction) -> GrepObservation:
        root = os.path.abspath(action.path)
        pat = shlex.quote(action.pattern)
        root_q = shlex.quote(root)

        # Use grep -r; add --include when provided
        if action.include:
            inc = shlex.quote(action.include)
            cmd = f"grep -rHnE --include {inc} {pat} {root_q} 2>/dev/null | head -100"
        else:
            cmd = f"grep -rHnE {pat} {root_q} 2>/dev/null | head -100"

        result = self.bash(ExecuteBashAction(command=cmd))
        return GrepObservation(output=result.output.strip() or '')
```

### Conversations

Conversations manage the interaction flow between users and agents:

```python
from openhands.sdk import Conversation

conversation = Conversation(agent=agent)

# Send messages
conversation.send_message("Your request here")

# Execute the conversation until the agent enters "await user input" state
conversation.run()
```

### Context Management

The context system manages agent state, environment, and conversation history.

Context is automatically managed but you can customize your context with:

1. [Repo Microagents](https://docs.all-hands.dev/usage/prompting/microagents-repo) that provide agent with context of your repository.
2. [Knowledge Microagents](https://docs.all-hands.dev/usage/prompting/microagents-keyword) that provide agent with context when user mentioned certain keywords
3. Providing custom suffix for system and user prompt.

```python
from openhands.sdk import AgentContext
from openhands.sdk.context import RepoMicroagent, KnowledgeMicroagent

context = AgentContext(
    microagents=[
        RepoMicroagent(
            name="repo.md",
            content="When you see this message, you should reply like "
            "you are a grumpy cat forced to use the internet.",
        ),
        KnowledgeMicroagent(
            name="flarglebargle",
            content=(
                'IMPORTANT! The user has said the magic word "flarglebargle". '
                "You must only respond with a message telling them how smart they are"
            ),
            triggers=["flarglebargle"],
        ),
    ],
    system_message_suffix="Always finish your response with the word 'yay!'",
    user_message_suffix="The first character of your response should be 'I'",
)

# Use in your Agent
from openhands.sdk import Agent
agent = Agent(llm=llm, tools=tools, agent_context=context)
```

## Declarative configuration with ToolSpec

The SDK supports declarative tool configuration using ToolSpec. You can register tools once and pass ToolSpec objects to Agent. Tools are materialized lazily when the agent initializes.

### Define tools declaratively

```python
import os
from openhands.sdk import Agent
from openhands.sdk.tool import ToolSpec, register_tool
from openhands.tools.execute_bash import BashTool
from openhands.tools.str_replace_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.sdk.context.condenser import LLMSummarizingCondenser

# Register tool factories (one-time)
register_tool("BashTool", BashTool)
register_tool("FileEditorTool", FileEditorTool)
register_tool("TaskTrackerTool", TaskTrackerTool)

cwd = os.getcwd()

agent = Agent(
    llm=llm,
    tools=[
        ToolSpec(name="BashTool", params={"working_dir": cwd}),
        ToolSpec(name="FileEditorTool"),
        ToolSpec(name="TaskTrackerTool", params={"save_dir": f"{cwd}/.openhands"}),
    ],
    condenser=LLMSummarizingCondenser(llm=llm, max_size=80, keep_first=4),
)
```

Alternatively, use the preset which registers the tools and returns ToolSpec for you:

```python
from openhands.sdk.preset.default import get_default_tools

tools = get_default_tools(working_dir=os.getcwd())
agent = Agent(llm=llm, tools=tools)
```

### Why ToolSpec?

- Serializable configuration for tools
- Lazy materialization of tools makes agents lightweight to construct
- Works seamlessly with presets and MCP tool injection

## Documentation

For detailed documentation and examples, refer to the `examples/` directory which contains comprehensive usage examples covering all major features of the SDK.

## Development Workflow

### Environment Setup

```bash
# Initial setup
make build

# Install additional dependencies
# add `--dev` if you want to install 
uv add package-name

# Update dependencies
uv sync
```

### Code Quality

The project enforces strict code quality standards:

```bash
# Format code
make format

# Lint code
make lint

# Run pre-commit hooks
uv run pre-commit run --all-files

# Type checking (included in pre-commit)
uv run pyright
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test suite
uv run pytest tests/cross/
uv run pytest tests/sdk/
uv run pytest tests/tools/

# Run with coverage
uv run pytest --cov=openhands --cov-report=html
```

### Pre-commit Workflow

Before every commit:

```bash
# Run on specific files
uv run pre-commit run --files path/to/file.py

# Run on all files
uv run pre-commit run --all-files
```
