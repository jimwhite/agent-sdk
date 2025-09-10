# openhands.tools.str_replace_editor.impl

## Classes

### FileEditorExecutor

Executor function type for a Tool.

## Functions

### file_editor(command: Literal['view', 'create', 'str_replace', 'insert', 'undo_edit'], path: str, file_text: str | None = None, view_range: list[int] | None = None, old_str: str | None = None, new_str: str | None = None, insert_line: int | None = None) -> openhands.tools.str_replace_editor.definition.StrReplaceEditorObservation

A global FileEditor instance to be used by the tool.

