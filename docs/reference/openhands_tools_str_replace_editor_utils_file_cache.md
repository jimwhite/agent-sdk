# openhands.tools.str_replace_editor.utils.file_cache

## Classes

### FileCache

A file-based cache with size limits and LRU eviction.

#### Functions

##### clear(self) -> None

Clear all entries from the cache.

##### delete(self, key: str) -> None

Delete a key from the cache.

##### get(self, key: str, default: Any = None) -> Any

Get a value from the cache.

##### set(self, key: str, value: Any) -> None

Set a value in the cache.

