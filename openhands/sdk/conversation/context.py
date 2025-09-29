"""Conversation context management for automatic event callback handling."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from openhands.sdk.conversation.types import ConversationCallbackType

# Global conversation context for automatic event callback handling
_current_event_dispatcher: "ConversationCallbackType | None" = None


def set_conversation_context(event_dispatcher: "ConversationCallbackType") -> None:
    """Set the current conversation context for automatic event handling.

    Args:
        event_dispatcher: Callback function that will be called for all events
                         created during this conversation context.
    """
    global _current_event_dispatcher
    _current_event_dispatcher = event_dispatcher


def get_conversation_context() -> "ConversationCallbackType | None":
    """Get the current conversation context.

    Returns:
        The current event dispatcher callback if in conversation context,
        None otherwise.
    """
    return _current_event_dispatcher


def clear_conversation_context() -> None:
    """Clear the current conversation context.

    This should be called when a conversation ends to prevent events
    from other conversations being handled incorrectly.
    """
    global _current_event_dispatcher
    _current_event_dispatcher = None
