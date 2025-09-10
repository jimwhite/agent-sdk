# openhands.tools.str_replace_editor.utils.encoding

Encoding management for file operations.

## Classes

### EncodingManager

Manages file encodings across multiple operations to ensure consistency.

#### Functions

##### detect_encoding(self, path: pathlib.Path) -> str

Detect the encoding of a file without handling caching logic.
Args:
    path: Path to the file
Returns:
    The detected encoding or default encoding if detection fails

##### get_encoding(self, path: pathlib.Path) -> str

Get encoding for a file, using cache or detecting if necessary.
Args:
    path: Path to the file
Returns:
    The encoding for the file

## Functions

### with_encoding(method)

Decorator to handle file encoding for file operations.
This decorator automatically detects and applies the correct encoding
for file operations, ensuring consistency between read and write operations.
Args:
    method: The method to decorate
Returns:
    The decorated method

