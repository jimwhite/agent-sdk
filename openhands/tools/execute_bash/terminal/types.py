"""Types for terminal session.

This is only used internally for terminal session management.
It is NOT exposed as part of the public tool interface.
"""

from pydantic import BaseModel, Field

from openhands.tools.execute_bash.constants import NO_CHANGE_TIMEOUT_SECONDS
from openhands.tools.execute_bash.metadata import CmdOutputMetadata


class ExecuteBashAction(BaseModel):
    """Schema for bash command execution."""

    command: str = Field(
        description="The bash command to execute. Can be empty string to view additional logs when previous exit code is `-1`. Can be `C-c` (Ctrl+C) to interrupt the currently running process. Note: You can only execute one bash command at a time. If you need to run multiple commands sequentially, you can use `&&` or `;` to chain them together."  # noqa
    )
    is_input: bool = Field(
        default=False,
        description="If True, the command is an input to the running process. If False, the command is a bash command to be executed in the terminal. Default is False.",  # noqa
    )
    timeout: float | None = Field(
        default=None,
        description=f"Optional. Sets a maximum time limit (in seconds) for running the command. If the command takes longer than this limit, you’ll be asked whether to continue or stop it. If you don’t set a value, the command will instead pause and ask for confirmation when it produces no new output for {NO_CHANGE_TIMEOUT_SECONDS} seconds. Use a higher value if the command is expected to take a long time (like installation or testing), or if it has a known fixed duration (like sleep).",  # noqa
    )


class ExecuteBashObservation(BaseModel):
    """A ToolResult that can be rendered as a CLI output."""

    output: str = Field(description="The raw output from the tool.")
    command: str | None = Field(
        default=None,
        description="The bash command that was executed. Can be empty string if the observation is from a previous command that hit soft timeout and is not yet finished.",  # noqa
    )
    exit_code: int | None = Field(
        default=None,
        description="The exit code of the command. -1 indicates the process hit the soft timeout and is not yet finished.",  # noqa
    )
    error: bool = Field(
        default=False,
        description="Whether there was an error during command execution.",
    )
    timeout: bool = Field(
        default=False, description="Whether the command execution timed out."
    )
    metadata: CmdOutputMetadata = Field(
        default_factory=CmdOutputMetadata,
        description="Additional metadata captured from PS1 after command execution.",
    )

    @property
    def command_id(self) -> int | None:
        """Get the command ID from metadata."""
        return self.metadata.pid
