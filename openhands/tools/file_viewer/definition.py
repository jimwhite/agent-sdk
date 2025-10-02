"""Read-only file viewer tool implementation."""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

from pydantic import Field


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState

from openhands.sdk.llm import ImageContent, TextContent
from openhands.sdk.tool import (
    Action,
    Observation,
    ToolAnnotations,
    ToolDefinition,
)


class FileViewerAction(Action):
    """Schema for read-only file viewing operations."""

    command: Literal["view", "list"] = Field(
        description="The command to run. 'view' displays file contents, "
        "'list' shows directory contents."
    )
    path: str = Field(description="Absolute path to file or directory.")
    view_range: list[int] | None = Field(
        default=None,
        description="Optional parameter for 'view' command. If provided, shows "
        "only the specified line range, e.g. [11, 12] shows lines 11 and 12. "
        "Indexing starts at 1. Setting [start_line, -1] shows all lines from "
        "start_line to the end of the file.",
    )


class FileViewerObservation(Observation):
    """Observation from read-only file viewing operations."""

    command: Literal["view", "list"] = Field(
        description="The command that was executed."
    )
    output: str = Field(
        default="", description="The output from the file viewing operation."
    )
    path: str | None = Field(default=None, description="The path that was viewed.")
    error: str | None = Field(default=None, description="Error message if any.")

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        if self.error:
            return [TextContent(text=self.error)]
        return [TextContent(text=self.output)]


TOOL_DESCRIPTION = (
    "Read-only file and directory viewer for planning and analysis.\n"
    "This tool provides safe, read-only access to view file contents and "
    "directory structures.\n\n"
    "* Use 'view' command to display file contents with optional line range\n"
    "* Use 'list' command to show directory contents up to 2 levels deep\n"
    "* Supports viewing text files, with line numbers for better reference\n"
    "* Binary files are handled gracefully with appropriate messages\n"
    "* No modification capabilities - purely for inspection and analysis\n\n"
    "This tool is ideal for planning agents that need to understand project "
    "structure and file contents without making any changes to the "
    "filesystem.\n\n"
    "Examples:\n"
    "- view /path/to/file.py - Show entire file with line numbers\n"
    "- view /path/to/file.py [10, 20] - Show lines 10-20\n"
    "- list /path/to/directory - Show directory contents"
)


file_viewer_tool = ToolDefinition(
    name="file_viewer",
    action_type=FileViewerAction,
    description=TOOL_DESCRIPTION,
    annotations=ToolAnnotations(
        title="file_viewer",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)


class FileViewerTool(ToolDefinition[FileViewerAction, FileViewerObservation]):
    """A read-only file viewer tool for planning agents."""

    @classmethod
    def create(
        cls,
        conv_state: "ConversationState",
    ) -> Sequence["FileViewerTool"]:
        """Initialize FileViewerTool with a FileViewerExecutor.

        Args:
            conv_state: Conversation state to get working directory from.
        """
        # Import here to avoid circular imports
        from openhands.tools.file_viewer.impl import FileViewerExecutor

        # Initialize the executor
        executor = FileViewerExecutor(workspace_root=conv_state.workspace.working_dir)

        # Add working directory information to the tool description
        working_dir = conv_state.workspace.working_dir
        enhanced_description = (
            f"{TOOL_DESCRIPTION}\n\n"
            f"Your current working directory is: {working_dir}\n"
            f"When exploring project structure, start with this directory."
        )

        # Initialize the parent Tool with the executor
        return [
            cls(
                name=file_viewer_tool.name,
                description=enhanced_description,
                action_type=FileViewerAction,
                observation_type=FileViewerObservation,
                annotations=file_viewer_tool.annotations,
                executor=executor,
            )
        ]
