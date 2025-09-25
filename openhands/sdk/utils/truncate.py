"""Utility functions for truncating text content."""

from datetime import datetime
from pathlib import Path

from openhands.sdk import get_logger


logger = get_logger(__name__)

# Default truncation limits
DEFAULT_TEXT_CONTENT_LIMIT = 50_000

# Default truncation notice
DEFAULT_TRUNCATE_NOTICE = (
    "<response clipped><NOTE>Due to the max output limit, only part of the full "
    "response has been shown to you.</NOTE>"
)


def _save_full_content(content: str, save_dir: str, tool_prefix: str) -> str | None:
    """Save full content to the specified directory and return the file path."""

    save_dir_path = Path(save_dir)
    save_dir_path.mkdir(exist_ok=True)

    # Generate a unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[
        :-3
    ]  # microseconds to milliseconds
    filename = f"{tool_prefix}_output_{timestamp}.txt"
    file_path = save_dir_path / filename

    try:
        file_path.write_text(content, encoding="utf-8")
        return str(file_path)
    except Exception as e:
        logger.debug(f"Failed to save full content to {file_path}: {e}")
        return None


def maybe_truncate(
    content: str,
    truncate_after: int | None = None,
    truncate_notice: str = DEFAULT_TRUNCATE_NOTICE,
    save_dir: str | None = None,
    tool_prefix: str = "output",
) -> str:
    """
    Truncate the middle of content if it exceeds the specified length.

    Keeps the head and tail of the content to preserve context at both ends.
    Optionally saves the full content to a file for later investigation.

    Args:
        content: The text content to potentially truncate
        truncate_after: Maximum length before truncation. If None, no truncation occurs
        truncate_notice: Notice to insert in the middle when content is truncated
        save_dir: Working directory to save full content file in
        tool_prefix: Prefix for the saved file (e.g., "bash", "browser", "editor")

    Returns:
        Original content if under limit, or truncated content with head and tail
        preserved and reference to saved file if applicable
    """
    if not truncate_after or len(content) <= truncate_after or truncate_after < 0:
        return content

    # truncate_after is too small to fit any content
    if len(truncate_notice) >= truncate_after:
        return truncate_notice[:truncate_after]

    # Save full content if requested
    saved_file_path = None
    if save_dir:
        saved_file_path = _save_full_content(content, save_dir, tool_prefix)

    # Calculate how much space we have for actual content
    available_chars = truncate_after - len(truncate_notice)
    orig_half = available_chars // 2

    # Give extra character to head if odd number
    orig_head_chars = orig_half + (available_chars % 2)

    # Create enhanced truncation notice with file reference if available
    enhanced_notice = truncate_notice
    if saved_file_path:
        # Calculate line number where truncation happens
        head_content_lines = len(content[:orig_head_chars].splitlines())

        enhanced_notice = (
            f"<response clipped><NOTE>Due to the max output limit, only part of the "
            f"full response has been shown to you. The complete output has been "
            f"saved to {saved_file_path} - you can use other tools "
            f"to view the full content (truncated part starts around "
            f"line {head_content_lines + 1}).</NOTE>"
        )

    # Calculate shifted number of tail characters
    shifted_available_chars = truncate_after - len(enhanced_notice)
    shifted_tail_chars = max(0, shifted_available_chars - orig_head_chars)

    # Keep head and tail, insert notice in the middle
    return content[:orig_head_chars] + enhanced_notice + content[-shifted_tail_chars:]
