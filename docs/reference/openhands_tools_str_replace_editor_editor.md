# openhands.tools.str_replace_editor.editor

## Classes

### FileEditor

An filesystem editor tool that allows the agent to
- view
- create
- navigate
- edit files
The tool parameters are defined by Anthropic and are not editable.

Original implementation: https://github.com/anthropics/anthropic-quickstarts/blob/main/computer-use-demo/computer_use_demo/tools/edit.py

#### Functions

##### insert(self, path: pathlib.Path, insert_line: int, new_str: str, encoding: str = 'utf-8') -> openhands.tools.str_replace_editor.definition.StrReplaceEditorObservation

Implement the insert command, which inserts new_str at the specified line
in the file content.

Args:
    path: Path to the file
    insert_line: Line number where to insert the new content
    new_str: Content to insert
    enable_linting: Whether to run linting on the changes
    encoding: The encoding to use (auto-detected by decorator)

##### read_file(self, path: pathlib.Path, start_line: int | None = None, end_line: int | None = None, encoding: str = 'utf-8') -> str

Read the content of a file from a given path; raise a ToolError if an
error occurs.

Args:
    path: Path to the file to read
    start_line: Optional start line number (1-based). If provided with
        end_line, only reads that range.
    end_line: Optional end line number (1-based). Must be provided with
        start_line.
    encoding: The encoding to use when reading the file (auto-detected by
        decorator)

##### str_replace(self, path: pathlib.Path, old_str: str, new_str: str | None) -> openhands.tools.str_replace_editor.definition.StrReplaceEditorObservation

Implement the str_replace command, which replaces old_str with new_str in
the file content.

Args:
    path: Path to the file
    old_str: String to replace
    new_str: Replacement string
    enable_linting: Whether to run linting on the changes
    encoding: The encoding to use (auto-detected by decorator)

##### undo_edit(self, path: pathlib.Path) -> openhands.tools.str_replace_editor.definition.StrReplaceEditorObservation

Implement the undo_edit command.

##### validate_file(self, path: pathlib.Path) -> None

Validate a file for reading or editing operations.

Args:
    path: Path to the file to validate

Raises:
    FileValidationError: If the file fails validation

##### validate_path(self, command: Literal['view', 'create', 'str_replace', 'insert', 'undo_edit'], path: pathlib.Path) -> None

Check that the path/command combination is valid.

Validates:
1. Path is absolute
2. Path and command are compatible

##### view(self, path: pathlib.Path, view_range: list[int] | None = None) -> openhands.tools.str_replace_editor.definition.StrReplaceEditorObservation

View the contents of a file or a directory.

##### write_file(self, path: pathlib.Path, file_text: str, encoding: str = 'utf-8') -> None

Write the content of a file to a given path; raise a ToolError if an
error occurs.

Args:
    path: Path to the file to write
    file_text: Content to write to the file
    encoding: The encoding to use when writing the file (auto-detected by
        decorator)

