# openhands.sdk.utils.truncate

Utility functions for truncating text content.

## Functions

### maybe_truncate(content: str, truncate_after: int | None = None, truncate_notice: str = '<response clipped><NOTE>Due to the max output limit, only part of the full response has been shown to you.</NOTE>') -> str

Truncate the middle of content if it exceeds the specified length.

Keeps the head and tail of the content to preserve context at both ends.

Args:
    content: The text content to potentially truncate
    truncate_after: Maximum length before truncation. If None, no truncation occurs
    truncate_notice: Notice to insert in the middle when content is truncated

Returns:
    Original content if under limit, or truncated content with head and tail
    preserved

