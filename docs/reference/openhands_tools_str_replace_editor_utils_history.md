# openhands.tools.str_replace_editor.utils.history

History management for file edits with disk-based storage and memory constraints.

## Classes

### FileHistoryManager

Manages file edit history with disk-based storage and memory constraints.

#### Functions

##### add_history(self, file_path: pathlib.Path, content: str)

Add a new history entry for a file.

##### clear_history(self, file_path: pathlib.Path)

Clear history for a given file.

##### get_all_history(self, file_path: pathlib.Path) -> List[str]

Get all history entries for a file.

##### get_metadata(self, file_path: pathlib.Path)

Get metadata for a file (for testing purposes).

##### pop_last_history(self, file_path: pathlib.Path) -> Optional[str]

Pop and return the most recent history entry for a file.

