"""Execute bash tool implementation."""

import os
from collections.abc import Sequence
from typing import Callable, Literal

from pydantic import BaseModel
from rich.text import Text

from openhands.sdk.llm import ImageContent, TextContent
from openhands.sdk.tool import (
    Schema,
    SchemaField,
    SchemaInstance,
    Tool,
    ToolAnnotations,
    ToolDataConverter,
)
from openhands.sdk.utils import maybe_truncate
from openhands.tools.execute_bash.constants import (
    MAX_CMD_OUTPUT_SIZE,
    NO_CHANGE_TIMEOUT_SECONDS,
)
from openhands.tools.execute_bash.metadata import CmdOutputMetadata


def make_input_schema() -> Schema:
    return Schema(
        name="openhands.tools.execute_bash.input",
        fields=[
            SchemaField.create(
                name="command",
                description="The bash command to execute. Can be empty string to "
                "view additional logs when previous exit code is `-1`. Can be "
                "`C-c` (Ctrl+C) to interrupt the currently running process. "
                "Note: You can only execute one bash command at a time. If you "
                "need to run multiple commands sequentially, you can use `&&` "
                "or `;` to chain them together.",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="is_input",
                description="If True, the command is an input to the running "
                "process. If False, the command is a bash command to be executed "
                "in the terminal. Default is False.",
                type=bool,
                required=False,
                default=False,
            ),
            SchemaField.create(
                name="timeout",
                description=f"Optional. Sets a maximum time limit (in seconds) "
                f"for running the command. If the command takes longer than this "
                f"limit, you'll be asked whether to continue or stop it. If you "
                f"don't set a value, the command will instead pause and ask for "
                f"confirmation when it produces no new output for "
                f"{NO_CHANGE_TIMEOUT_SECONDS} seconds. Use a higher value if the "
                f"command is expected to take a long time (like installation or "
                f"testing), or if it has a known fixed duration (like sleep).",
                type=float,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            ),
        ],
    )


def make_output_schema() -> Schema:
    return Schema(
        name="openhands.tools.execute_bash.output",
        fields=[
            SchemaField.create(
                name="output",
                description="The raw output from the tool.",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="command",
                description="The bash command that was executed. Can be empty "
                "string if the observation is from a previous command that hit "
                "soft timeout and is not yet finished.",
                type=str,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="exit_code",
                description="The exit code of the command. -1 indicates the "
                "process hit the soft timeout and is not yet finished.",
                type=int,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="error",
                description="Whether there was an error during command execution.",
                type=bool,
                required=False,
                default=False,
            ),
            SchemaField.create(
                name="timeout",
                description="Whether the command execution timed out.",
                type=bool,
                required=False,
                default=False,
            ),
            SchemaField.create(
                name="metadata",
                description="Additional metadata captured from PS1 after "
                "command execution.",
                type=dict[str, str],
                required=False,
                default=None,
            ),
        ],
    )


class ExecuteBashDataConverter(ToolDataConverter):
    """Data converter for ExecuteBash tool."""

    def agent_observation(
        self, observation: SchemaInstance
    ) -> Sequence[TextContent | ImageContent]:
        observation.validate_data()

        # Extract metadata if present
        metadata_dict = observation.data.get("metadata", {})
        if isinstance(metadata_dict, dict):
            metadata = CmdOutputMetadata(**metadata_dict)
        else:
            metadata = CmdOutputMetadata()

        output = observation.data.get("output", "")
        error = observation.data.get("error", False)

        ret = f"{metadata.prefix}{output}{metadata.suffix}"
        if metadata.working_dir:
            ret += f"\n[Current working directory: {metadata.working_dir}]"
        if metadata.py_interpreter_path:
            ret += f"\n[Python interpreter: {metadata.py_interpreter_path}]"
        if metadata.exit_code != -1:
            ret += f"\n[Command finished with exit code {metadata.exit_code}]"
        if error:
            ret = f"[There was an error during command execution.]\n{ret}"

        return [TextContent(text=maybe_truncate(ret, MAX_CMD_OUTPUT_SIZE))]

    def visualize_action(self, action: SchemaInstance) -> Text:
        """Return Rich Text representation with PS1-style bash prompt."""
        action.validate_data()
        content = Text()

        # Create PS1-style prompt
        content.append("$ ", style="bold green")

        # Add command with syntax highlighting
        command = action.data.get("command", "")
        if command:
            content.append(command, style="white")
        else:
            content.append("[empty command]", style="dim italic")

        # Add metadata if present
        is_input = action.data.get("is_input", False)
        if is_input:
            content.append(" ", style="white")
            content.append("(input to running process)", style="dim yellow")

        timeout = action.data.get("timeout")
        if timeout is not None:
            content.append(" ", style="white")
            content.append(f"[timeout: {timeout}s]", style="dim cyan")

        return content

    def visualize_observation(self, observation: SchemaInstance) -> Text:
        """Return Rich Text representation with terminal-style output formatting."""
        observation.validate_data()
        content = Text()

        error = observation.data.get("error", False)
        output = observation.data.get("output", "")
        metadata_dict = observation.data.get("metadata", {})

        if isinstance(metadata_dict, dict):
            metadata = CmdOutputMetadata(**metadata_dict)
        else:
            metadata = CmdOutputMetadata()

        # Add error indicator if present
        if error:
            content.append("❌ ", style="red bold")
            content.append("Command execution error\n", style="red")

        # Add command output with proper styling
        if output:
            # Style the output based on content
            output_lines = output.split("\n")
            for line in output_lines:
                if line.strip():
                    # Color error-like lines differently
                    if any(
                        keyword in line.lower()
                        for keyword in ["error", "failed", "exception", "traceback"]
                    ):
                        content.append(line, style="red")
                    elif any(
                        keyword in line.lower() for keyword in ["warning", "warn"]
                    ):
                        content.append(line, style="yellow")
                    elif line.startswith("+ "):  # bash -x output
                        content.append(line, style="dim cyan")
                    else:
                        content.append(line, style="white")
                content.append("\n")

        # Add metadata with styling
        if metadata:
            if metadata.working_dir:
                content.append("\n📁 ", style="blue")
                content.append(
                    f"Working directory: {metadata.working_dir}", style="dim blue"
                )

            if metadata.py_interpreter_path:
                content.append("\n🐍 ", style="green")
                content.append(
                    f"Python interpreter: {metadata.py_interpreter_path}",
                    style="dim green",
                )

            if metadata.exit_code is not None:
                if metadata.exit_code == 0:
                    content.append("\n✅ ", style="green")
                    content.append(f"Exit code: {metadata.exit_code}", style="green")
                elif metadata.exit_code == -1:
                    content.append("\n⏳ ", style="yellow")
                    content.append(
                        "Process still running (soft timeout)", style="yellow"
                    )
                else:
                    content.append("\n❌ ", style="red")
                    content.append(f"Exit code: {metadata.exit_code}", style="red")

        return content


TOOL_DESCRIPTION = """Execute a bash command in the terminal within a persistent shell session.


### Command Execution
* One command at a time: You can only execute one bash command at a time. If you need to run multiple commands sequentially, use `&&` or `;` to chain them together.
* Persistent session: Commands execute in a persistent shell session where environment variables, virtual environments, and working directory persist between commands.
* Soft timeout: Commands have a soft timeout of 10 seconds, once that's reached, you have the option to continue or interrupt the command (see section below for details)
* Shell options: Do NOT use `set -e`, `set -eu`, or `set -euo pipefail` in shell scripts or commands in this environment. The runtime may not support them and can cause unusable shell sessions. If you want to run multi-line bash commands, write the commands to a file and then run it, instead.

### Long-running Commands
* For commands that may run indefinitely, run them in the background and redirect output to a file, e.g. `python3 app.py > server.log 2>&1 &`.
* For commands that may run for a long time (e.g. installation or testing commands), or commands that run for a fixed amount of time (e.g. sleep), you should set the "timeout" parameter of your function call to an appropriate value.
* If a bash command returns exit code `-1`, this means the process hit the soft timeout and is not yet finished. By setting `is_input` to `true`, you can:
  - Send empty `command` to retrieve additional logs
  - Send text (set `command` to the text) to STDIN of the running process
  - Send control commands like `C-c` (Ctrl+C), `C-d` (Ctrl+D), or `C-z` (Ctrl+Z) to interrupt the process
  - If you do C-c, you can re-start the process with a longer "timeout" parameter to let it run to completion

### Best Practices
* Directory verification: Before creating new directories or files, first verify the parent directory exists and is the correct location.
* Directory management: Try to maintain working directory by using absolute paths and avoiding excessive use of `cd`.

### Output Handling
* Output truncation: If the output exceeds a maximum length, it will be truncated before being returned.
"""  # noqa


class BashTool(Tool):
    """A Tool subclass that automatically initializes a BashExecutor with auto-detection."""  # noqa: E501

    @classmethod
    def create(
        cls,
        working_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int | None = None,
        terminal_type: Literal["tmux", "subprocess"] | None = None,
        env_provider: Callable[[str], dict[str, str]] | None = None,
        env_masker: Callable[[str], str] | None = None,
    ) -> "BashTool":
        """Initialize BashTool with executor parameters.

        Args:
            working_dir: The working directory for bash commands
            username: Optional username for the bash session
            no_change_timeout_seconds: Timeout for no output change
            terminal_type: Force a specific session type:
                         ('tmux', 'subprocess').
                         If None, auto-detect based on system capabilities:
                         - On Windows: PowerShell if available, otherwise subprocess
                         - On Unix-like: tmux if available, otherwise subprocess
            env_provider: Optional callable that maps a command string to
                          environment variables (key -> value) to export before
                          running that command.
            env_masker: Optional callable that returns current secret values
                        for masking purposes. This ensures consistent masking
                        even when env_provider calls fail.
        """
        # Import here to avoid circular imports
        from openhands.tools.execute_bash.impl import BashExecutor

        if not os.path.isdir(working_dir):
            raise ValueError(f"working_dir '{working_dir}' is not a valid directory")

        # Create input and output schemas
        input_schema = make_input_schema()
        output_schema = make_output_schema()

        # Initialize the executor
        executor = BashExecutor(
            working_dir=working_dir,
            username=username,
            no_change_timeout_seconds=no_change_timeout_seconds,
            terminal_type=terminal_type,
            env_provider=env_provider,
            env_masker=env_masker,
        )

        # Initialize the parent Tool with the executor
        return cls(
            name="execute_bash",
            description=TOOL_DESCRIPTION,
            input_schema=input_schema,
            output_schema=output_schema,
            annotations=ToolAnnotations(
                title="execute_bash",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
                openWorldHint=True,
            ),
            executor=executor,
            data_converter=ExecuteBashDataConverter(),
        )


# Compatibility classes for terminal system


class ExecuteBashAction(BaseModel):
    """Compatibility class for terminal system."""

    command: str
    is_input: bool = False
    timeout: int | None = None


class ExecuteBashObservation(BaseModel):
    """Compatibility class for terminal system."""

    output: str
    command: str | None = None
    exit_code: int | None = None
    error: bool = False
    timeout: bool = False
    metadata: dict | None = None
