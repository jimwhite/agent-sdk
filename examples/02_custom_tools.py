"""Advanced example showing explicit executor usage and custom grep tool."""

import os
import shlex

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    LLMConvertibleEvent,
    Message,
    TextContent,
    Tool,
    get_logger,
)
from openhands.sdk.tool import (
    Schema,
    SchemaField,
    SchemaInstance,
    ToolExecutor,
)
from openhands.tools import BashExecutor, BashTool, FileEditorTool


logger = get_logger(__name__)


# --- Action / Observation Schemas ---


class GrepExecutor(ToolExecutor):
    def __init__(self, bash: BashExecutor):
        self.bash = bash

    def __call__(self, action: SchemaInstance) -> SchemaInstance:
        action.validate_data()
        pattern = str(action.data.get("pattern", ""))
        path = str(action.data.get("path", "."))
        include = action.data.get("include")

        root = os.path.abspath(path)
        pat = shlex.quote(pattern)
        root_q = shlex.quote(root)

        if include:
            inc = shlex.quote(str(include))
            cmd = f"grep -rHnE --include {inc} {pat} {root_q} 2>/dev/null | head -100"
        else:
            cmd = f"grep -rHnE {pat} {root_q} 2>/dev/null | head -100"

        from openhands.tools.execute_bash.definition import make_input_schema
        result = self.bash(SchemaInstance(
            definition=make_input_schema(),
            data={"command": cmd, "is_input": False}
        ))

        matches: list[str] = []
        files: set[str] = set()

        output = str(result.data.get("output", ""))

        if output.strip():
            for line in output.strip().splitlines():
                matches.append(line)
                file_path = line.split(":", 1)[0]
                if file_path:
                    files.add(os.path.abspath(file_path))

        return SchemaInstance(
            name="GrepObservation",
            definition=action.definition,
            data={
                "matches": matches,
                "files": sorted(files),
                "count": len(matches),
            },
        )


# Tool description
_GREP_DESCRIPTION = """Fast content search tool.
* Searches file contents using regular expressions
* Supports full regex syntax (eg. "log.*Error", "function\\s+\\w+", etc.)
* Filter files by pattern with the include parameter (eg. "*.js", "*.{ts,tsx}")
* Returns matching file paths sorted by modification time.
* Only the first 100 results are returned. Consider narrowing your search with stricter regex patterns or provide path parameter if you need more results.
* Use this tool when you need to find files containing specific patterns
* When you are doing an open ended search that may require multiple rounds of globbing and grepping, use the Agent tool instead
"""  # noqa: E501

# Configure LLM
api_key = os.getenv("LITELLM_API_KEY")
assert api_key is not None, "LITELLM_API_KEY environment variable is not set."
llm = LLM(
    model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
    base_url="https://llm-proxy.eval.all-hands.dev",
    api_key=SecretStr(api_key),
)

# Tools - demonstrating both simplified and advanced patterns
cwd = os.getcwd()

# Advanced pattern: explicit executor creation and reuse
bash_executor = BashExecutor(working_dir=cwd)
bash_tool_advanced = BashTool.create(working_dir=cwd, executor=bash_executor)

# Create the grep tool using explicit executor that reuses the bash executor
grep_executor = GrepExecutor(bash_executor)
grep_tool = Tool(
    name="grep",
    description=_GREP_DESCRIPTION,
    input_schema=Schema(
        type="action",
        fields=[
            SchemaField.create(
                name="pattern",
                description="Regex to search for",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="path",
                description="Directory to search (absolute or relative)",
                type=str,
                required=False,
                default=".",
            ),
            SchemaField.create(
                name="include",
                description="Optional glob to filter files (e.g. '*.py')",
                type=str,
                required=False,
                default=None,
            ),
        ],
    ),
    output_schema=Schema(
        type="observation",
        fields=[
            SchemaField.create(
                name="matches",
                description="List of matching lines",
                type=list[str],
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="files",
                description="List of files that contain matches",
                type=list[str],
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="count",
                description="Total number of matches",
                type=int,
                required=True,
            ),
        ],
    ),
    executor=grep_executor,
)

tools = [
    # Simplified pattern
    FileEditorTool.create(),
    # Advanced pattern with explicit executor
    bash_tool_advanced,
    # Custom tool with explicit executor
    grep_tool,
]

# Agent
agent = Agent(llm=llm, tools=tools)

llm_messages = []  # collect raw LLM messages


def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())


conversation = Conversation(agent=agent, callbacks=[conversation_callback])

conversation.send_message(
    message=Message(
        role="user",
        content=[
            TextContent(
                text=(
                    "Hello! Can you use the grep tool to find all files "
                    "containing the word 'class' in this project, then create a summary file listing them? "  # noqa: E501
                    "Use the pattern 'class' to search and include only Python files with '*.py'."  # noqa: E501
                )
            )
        ],
    )
)
conversation.run()

conversation.send_message(
    message=Message(
        role="user",
        content=[TextContent(text=("Great! Now delete that file."))],
    )
)
conversation.run()

print("=" * 100)
print("Conversation finished. Got the following LLM messages:")
for i, message in enumerate(llm_messages):
    print(f"Message {i}: {str(message)[:200]}")
