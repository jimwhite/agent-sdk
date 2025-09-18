"""String replace editor tool implementation."""

from collections.abc import Sequence

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
from openhands.sdk.tool.tool import ToolExecutor
from openhands.tools.str_replace_editor.utils.diff import visualize_diff


COMMAND_LIST = ["view", "create", "str_replace", "insert", "undo_edit"]


def make_input_schema(workspace_path: str) -> Schema:
    return Schema(
        type="action",
        fields=[
            SchemaField.create(
                name="command",
                description="The commands to run. Allowed options are: `view`, "
                "`create`, `str_replace`, `insert`, `undo_edit`.",
                type=str,
                required=True,
                enum=COMMAND_LIST,
            ),
            SchemaField.create(
                name="path",
                description=f"Absolute path to file or directory, e.g. "
                f"`{workspace_path}/file.py` or `{workspace_path}`.",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="file_text",
                description="Required parameter of `create` command, with the content"
                " of the file to be created.",
                type=str,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="old_str",
                type=str,
                required=False,
                default=None,
                description="Required parameter of `str_replace` command containing "
                "the string in `path` to replace.",
            ),
            SchemaField.create(
                name="new_str",
                description="Optional parameter of `str_replace` command containing "
                "the new string (if not given, no string will be added). "
                "Required parameter of `insert` command containing the "
                "string to insert.",
                type=str,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="insert_line",
                description="Required parameter of `insert` command. The `new_str` "
                "will be inserted AFTER the line `insert_line` of `path`.",
                type=int,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="view_range",
                description="Optional parameter of `view` command when `path` points "
                "to a file. If none is given, the full file is shown. "
                "If provided, the file will be shown in the indicated line number "
                "range, e.g. [11, 12] will show lines 11 and 12. Indexing at 1 to "
                "start. Setting `[start_line, -1]` shows all lines from `start_line` "
                "to the end of the file.",
                type=list[int],
                required=False,
                default=None,
            ),
        ],
    )


def make_output_schema() -> Schema:
    return Schema(
        type="observation",
        fields=[
            SchemaField.create(
                name="command",
                description="The commands to run. Allowed options are: `view`, "
                "`create`, `str_replace`, `insert`, `undo_edit`.",
                type=str,
                required=True,
                enum=COMMAND_LIST,
            ),
            SchemaField.create(
                name="output",
                description="The output message from the tool for the LLM to see.",
                type=str,
                required=True,
            ),
            SchemaField.create(
                name="path",
                description="The file path that was edited.",
                type=str,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="prev_exist",
                description="Indicates if the file previously "
                "existed. If not, it was created.",
                type=bool,
                required=True,
            ),
            SchemaField.create(
                name="old_content",
                description="The content of the file before the edit.",
                type=str,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="new_content",
                description="The content of the file after the edit.",
                type=str,
                required=False,
                default=None,
            ),
            SchemaField.create(
                name="error",
                description="Error message if any.",
                type=str,
                required=False,
                default=None,
            ),
        ],
    )


class StrReplaceEditorDataConverter(ToolDataConverter):
    """Data converter for StrReplaceEditor tool."""

    def agent_observation(
        self, observation: SchemaInstance
    ) -> Sequence[TextContent | ImageContent]:
        observation.validate_data()
        if observation.data["error"]:
            return [TextContent(text=observation.data["error"])]
        return [TextContent(text=observation.data["output"])]

    def visualize_observation(self, observation: SchemaInstance) -> Text:
        """Return Rich Text representation of this observation.

        Shows diff visualization for meaningful changes (file creation, successful
        edits), otherwise falls back to agent observation.
        """
        observation.validate_data()

        if not self._has_meaningful_diff(observation):
            return super().visualize_observation(observation)

        path = observation.data.get("path")
        old_content = observation.data.get("old_content")
        new_content = observation.data.get("new_content")
        command = observation.data.get("command")
        error = observation.data.get("error")

        assert path is not None, "path should be set for meaningful diff"
        # Generate and cache diff visualization
        if not self._diff_cache:
            change_applied = command != "view" and not error
            self._diff_cache = visualize_diff(
                path,
                old_content,
                new_content,
                n_context_lines=2,
                change_applied=change_applied,
            )

        return self._diff_cache

    def _has_meaningful_diff(self, observation: SchemaInstance) -> bool:
        """Check if there's a meaningful diff to display."""
        path = observation.data.get("path")
        old_content = observation.data.get("old_content")
        new_content = observation.data.get("new_content")
        command = observation.data.get("command")
        error = observation.data.get("error")
        prev_exist = observation.data.get("prev_exist")

        if error:
            return False
        if not path:
            return False
        if command not in ("create", "str_replace", "insert", "undo_edit"):
            return False
        # File creation case
        if command == "create" and new_content and not prev_exist:
            return True
        # File modification cases (str_replace, insert, undo_edit)
        if command in ("str_replace", "insert", "undo_edit"):
            # Need both old and new content to show meaningful diff
            if old_content is not None and new_content is not None:
                # Only show diff if content actually changed
                return old_content != new_content
        return False


TOOL_DESCRIPTION = """Custom editing tool for viewing, creating and editing files in plain-text format
* State is persistent across command calls and discussions with the user
* If `path` is a text file, `view` displays the result of applying `cat -n`. If `path` is a directory, `view` lists non-hidden files and directories up to 2 levels deep
* The following binary file extensions can be viewed in Markdown format: [".xlsx", ".pptx", ".wav", ".mp3", ".m4a", ".flac", ".pdf", ".docx"]. IT DOES NOT HANDLE IMAGES.
* The `create` command cannot be used if the specified `path` already exists as a file
* If a `command` generates a long output, it will be truncated and marked with `<response clipped>`
* The `undo_edit` command will revert the last edit made to the file at `path`
* This tool can be used for creating and editing files in plain-text format.


Before using this tool:
1. Use the view tool to understand the file's contents and context
2. Verify the directory path is correct (only applicable when creating new files):
   - Use the view tool to verify the parent directory exists and is the correct location

When making edits:
   - Ensure the edit results in idiomatic, correct code
   - Do not leave the code in a broken state
   - Always use absolute file paths (starting with /)

CRITICAL REQUIREMENTS FOR USING THIS TOOL:

1. EXACT MATCHING: The `old_str` parameter must match EXACTLY one or more consecutive lines from the file, including all whitespace and indentation. The tool will fail if `old_str` matches multiple locations or doesn't match exactly with the file content.

2. UNIQUENESS: The `old_str` must uniquely identify a single instance in the file:
   - Include sufficient context before and after the change point (3-5 lines recommended)
   - If not unique, the replacement will not be performed

3. REPLACEMENT: The `new_str` parameter should contain the edited lines that replace the `old_str`. Both strings must be different.

Remember: when making multiple file edits in a row to the same file, you should prefer to send all edits in a single message with multiple calls to this tool, rather than multiple messages with a single call each.
"""  # noqa: E501


class FileEditorTool(Tool):
    """A Tool subclass that automatically initializes a FileEditorExecutor."""

    @classmethod
    def create(
        cls, workspace_root: str | None = None, executor: ToolExecutor | None = None
    ) -> "FileEditorTool":
        """Initialize FileEditorTool with a FileEditorExecutor.

        Args:
            workspace_root: Root directory for file operations. If provided,
                          tool descriptions will use this path in examples.
        """
        # Import here to avoid circular imports
        from openhands.tools.str_replace_editor.impl import FileEditorExecutor

        # Determine the workspace path for examples
        workspace_path = workspace_root if workspace_root else "/workspace"

        # Create input and output schemas
        input_schema = make_input_schema(workspace_path=workspace_path)
        output_schema = make_output_schema()

        # Initialize the executor
        if executor is None:
            executor = FileEditorExecutor(workspace_root=workspace_path)

        # Initialize the parent Tool with the executor
        return cls(
            name="str_replace_editor",
            description=TOOL_DESCRIPTION,
            input_schema=input_schema,
            output_schema=output_schema,
            annotations=ToolAnnotations(
                title="str_replace_editor",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
                openWorldHint=False,
            ),
            executor=executor,
            data_converter=StrReplaceEditorDataConverter(),
        )
