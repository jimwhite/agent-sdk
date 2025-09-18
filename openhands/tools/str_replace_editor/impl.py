from openhands.sdk.tool import ToolExecutor
from openhands.sdk.tool.schema import SchemaInstance
from openhands.tools.str_replace_editor.definition import (
    CommandLiteral,
    StrReplaceEditorAction,
    StrReplaceEditorObservation,
    make_output_schema,
)
from openhands.tools.str_replace_editor.editor import FileEditor
from openhands.tools.str_replace_editor.exceptions import ToolError


# Module-global editor instance (lazily initialized in file_editor)
_GLOBAL_EDITOR: FileEditor | None = None


class FileEditorExecutor(ToolExecutor):
    def __init__(self, workspace_root: str | None = None):
        self.editor = FileEditor(workspace_root=workspace_root)

    def __call__(
        self, action: SchemaInstance | StrReplaceEditorAction
    ) -> SchemaInstance:
        # Handle both SchemaInstance and StrReplaceEditorAction for compatibility
        if isinstance(action, StrReplaceEditorAction):
            editor_action = action
        else:
            # Convert SchemaInstance to StrReplaceEditorAction for editor system
            editor_action = StrReplaceEditorAction(
                command=action.data.get("command"),
                path=action.data.get("path"),
                file_text=action.data.get("file_text"),
                view_range=action.data.get("view_range"),
                old_str=action.data.get("old_str"),
                new_str=action.data.get("new_str"),
                insert_line=action.data.get("insert_line"),
            )

        result: StrReplaceEditorObservation | None = None
        try:
            result = self.editor(
                command=editor_action.command,
                path=editor_action.path,
                file_text=editor_action.file_text,
                view_range=editor_action.view_range,
                old_str=editor_action.old_str,
                new_str=editor_action.new_str,
                insert_line=editor_action.insert_line,
            )
        except ToolError as e:
            result = StrReplaceEditorObservation(
                command=editor_action.command, output="", error=e.message
            )
        assert result is not None, "file_editor should always return a result"

        # Convert StrReplaceEditorObservation back to SchemaInstance
        return SchemaInstance(
            name="str_replace_editor_output",
            definition=make_output_schema(),
            data={
                "command": result.command,
                "output": result.output,
                "error": result.error,
                "path": result.path,
                "old_content": result.old_content,
                "new_content": result.new_content,
                "prev_exist": result.prev_exist,
            },
        )


def file_editor(
    command: CommandLiteral,
    path: str,
    file_text: str | None = None,
    view_range: list[int] | None = None,
    old_str: str | None = None,
    new_str: str | None = None,
    insert_line: int | None = None,
) -> StrReplaceEditorObservation:
    """A global FileEditor instance to be used by the tool."""

    global _GLOBAL_EDITOR
    if _GLOBAL_EDITOR is None:
        _GLOBAL_EDITOR = FileEditor()

    result: StrReplaceEditorObservation | None = None
    try:
        result = _GLOBAL_EDITOR(
            command=command,
            path=path,
            file_text=file_text,
            view_range=view_range,
            old_str=old_str,
            new_str=new_str,
            insert_line=insert_line,
        )
    except ToolError as e:
        result = StrReplaceEditorObservation(
            command=command, output="", error=e.message
        )
    assert result is not None, "file_editor should always return a result"
    return result
