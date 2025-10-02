"""Global conversation registry for managing all conversations."""

import json
import os
import threading
import uuid
from typing import TYPE_CHECKING, Optional

from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.logger import get_logger


if TYPE_CHECKING:
    from openhands.sdk.agent.base import AgentBase
    from openhands.sdk.conversation.base import BaseConversation

logger = get_logger(__name__)


class ConversationRegistry:
    """Global registry for managing all conversations with parent-child relationships."""  # noqa: E501

    _instance: Optional["ConversationRegistry"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ConversationRegistry":
        """Singleton pattern to ensure only one registry instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the registry if not already initialized."""
        if not getattr(self, "_initialized", False):
            self._conversations: dict[ConversationID, BaseConversation] = {}
            self._parent_child_map: dict[ConversationID, set[ConversationID]] = {}
            self._child_parent_map: dict[ConversationID, ConversationID] = {}
            self._registry_lock = threading.RLock()
            self._initialized = True
            logger.debug("ConversationRegistry initialized")

    def register(
        self, conversation: "BaseConversation", parent_id: ConversationID | None = None
    ) -> None:
        """Register a conversation in the global pool.

        Args:
            conversation: The conversation to register
            parent_id: Optional parent conversation ID for child conversations
        """
        with self._registry_lock:
            conversation_id = conversation.id
            self._conversations[conversation_id] = conversation

            # Handle parent-child relationship
            if parent_id is not None:
                # Add to parent's children set
                if parent_id not in self._parent_child_map:
                    self._parent_child_map[parent_id] = set()
                self._parent_child_map[parent_id].add(conversation_id)

                # Set child's parent
                self._child_parent_map[conversation_id] = parent_id

                logger.debug(
                    f"Registered child conversation {conversation_id} "
                    f"with parent {parent_id}"
                )
            else:
                logger.debug(f"Registered root conversation {conversation_id}")

    def unregister(self, conversation_id: ConversationID) -> None:
        """Unregister a conversation from the global pool.

        Args:
            conversation_id: The ID of the conversation to unregister
        """
        with self._registry_lock:
            if conversation_id not in self._conversations:
                logger.warning(
                    f"Attempted to unregister non-existent conversation "
                    f"{conversation_id}"
                )
                return

            # Remove from conversations
            del self._conversations[conversation_id]

            # Handle parent-child relationships
            if conversation_id in self._child_parent_map:
                # Remove from parent's children set
                parent_id = self._child_parent_map[conversation_id]
                if parent_id in self._parent_child_map:
                    self._parent_child_map[parent_id].discard(conversation_id)
                    if not self._parent_child_map[parent_id]:
                        del self._parent_child_map[parent_id]
                del self._child_parent_map[conversation_id]

            # Remove any children relationships (this conversation was a parent)
            if conversation_id in self._parent_child_map:
                child_ids = self._parent_child_map[conversation_id].copy()
                for child_id in child_ids:
                    if child_id in self._child_parent_map:
                        del self._child_parent_map[child_id]
                del self._parent_child_map[conversation_id]

            logger.debug(f"Unregistered conversation {conversation_id}")

    def get(self, conversation_id: ConversationID) -> Optional["BaseConversation"]:
        """Get a conversation by ID.

        Args:
            conversation_id: The ID of the conversation to retrieve

        Returns:
            The conversation instance, or None if not found
        """
        with self._registry_lock:
            return self._conversations.get(conversation_id)

    def get_parent(
        self, conversation_id: ConversationID
    ) -> Optional["BaseConversation"]:
        """Get the parent conversation of a child conversation.

        Args:
            conversation_id: The ID of the child conversation

        Returns:
            The parent conversation instance, or None if not found or no parent
        """
        with self._registry_lock:
            parent_id = self._child_parent_map.get(conversation_id)
            if parent_id is not None:
                return self._conversations.get(parent_id)
            return None

    def get_children(self, conversation_id: ConversationID) -> list["BaseConversation"]:
        """Get all child conversations of a parent conversation.

        Args:
            conversation_id: The ID of the parent conversation

        Returns:
            List of child conversation instances
        """
        with self._registry_lock:
            child_ids = self._parent_child_map.get(conversation_id, set())
            children = []
            for child_id in child_ids:
                child = self._conversations.get(child_id)
                if child is not None:
                    children.append(child)
            return children

    def get_child_ids(self, conversation_id: ConversationID) -> list[ConversationID]:
        """Get all child conversation IDs of a parent conversation.

        Args:
            conversation_id: The ID of the parent conversation

        Returns:
            List of child conversation IDs
        """
        with self._registry_lock:
            return list(self._parent_child_map.get(conversation_id, set()))

    def list_all(self) -> list[ConversationID]:
        """List all registered conversation IDs.

        Returns:
            List of all conversation IDs in the registry
        """
        with self._registry_lock:
            return list(self._conversations.keys())

    def create_child_conversation(
        self,
        parent_id: ConversationID,
        agent: "AgentBase",
        working_dir: str | None = None,
        **kwargs,
    ) -> "BaseConversation":
        """Create a child conversation with the specified agent.

        Args:
            parent_id: The ID of the parent conversation
            agent: The agent to use for the child conversation
            working_dir: Working directory for the child. If None, creates a
                        directory under .conversations/{parent-uuid}/{child-uuid}/
            **kwargs: Additional arguments passed to LocalConversation

        Returns:
            The child conversation instance

        Raises:
            ValueError: If parent conversation not found
        """
        with self._registry_lock:
            parent = self._conversations.get(parent_id)
            if parent is None:
                raise ValueError(f"Parent conversation {parent_id} not found")

            # Import here to avoid circular imports
            from typing import cast

            from openhands.sdk.conversation.impl.local_conversation import (
                LocalConversation,
            )

            child_id = uuid.uuid4()

            # Generate working directory if not provided
            if working_dir is None:
                conversations_dir = os.path.join(
                    parent.state.workspace.working_dir, ".conversations"
                )
                parent_dir = os.path.join(conversations_dir, str(parent_id))
                working_dir = os.path.join(parent_dir, str(child_id))
                os.makedirs(working_dir, exist_ok=True)

                # Update children.json mapping
                children_file = os.path.join(parent_dir, "children.json")
                children_mapping = {}
                if os.path.exists(children_file):
                    with open(children_file) as f:
                        children_mapping = json.load(f)

                # Add child to mapping with agent type
                agent_type = agent.__class__.__name__.replace("Agent", "").lower()
                children_mapping[str(child_id)] = {
                    "agent_type": agent_type,
                    "agent_class": agent.__class__.__name__,
                    "created_at": str(uuid.uuid1().time),
                }

                with open(children_file, "w") as f:
                    json.dump(children_mapping, f, indent=2)

            # Create child conversation with parent reference
            child = LocalConversation(
                agent=agent,
                workspace=working_dir,
                conversation_id=child_id,
                persistence_dir=parent.state.persistence_dir,
                callbacks=cast(list, kwargs.get("callbacks"))
                if "callbacks" in kwargs
                else None,
                max_iteration_per_run=cast(
                    int, kwargs.get("max_iteration_per_run", 10)
                ),
                stuck_detection=cast(bool, kwargs.get("stuck_detection", True)),
                visualize=cast(bool, kwargs.get("visualize", False)),
            )

            # Set parent_id in child state
            with child._state:
                child._state.parent_id = parent_id

            # Set parent conversation reference in child
            child._parent_conversation = parent  # type: ignore[attr-defined]

            # Update parent-child relationship (child already registered itself in __init__)  # noqa: E501
            if parent_id not in self._parent_child_map:
                self._parent_child_map[parent_id] = set()
            self._parent_child_map[parent_id].add(child_id)
            self._child_parent_map[child_id] = parent_id

            logger.info(
                f"Created child conversation {child_id} with agent type "
                f"{agent.__class__.__name__} in {working_dir}"
            )

            return child

    def get_child_conversation(
        self, parent_id: ConversationID, child_id: ConversationID
    ) -> Optional["BaseConversation"]:
        """Get a child conversation by ID.

        Args:
            parent_id: The ID of the parent conversation
            child_id: The ID of the child conversation

        Returns:
            The child conversation instance, or None if not found or not a child of
            parent
        """
        with self._registry_lock:
            child = self._conversations.get(child_id)
            if child is not None:
                # Verify it's actually a child of the specified parent
                actual_parent_id = self._child_parent_map.get(child_id)
                if actual_parent_id == parent_id:
                    return child
            return None

    def get_parent_conversation(
        self, child_id: ConversationID
    ) -> Optional["BaseConversation"]:
        """Get the parent conversation of a child conversation.

        Args:
            child_id: The ID of the child conversation

        Returns:
            The parent conversation instance, or None if not found or no parent
        """
        return self.get_parent(child_id)

    def close_child_conversation(
        self, parent_id: ConversationID, child_id: ConversationID
    ) -> None:
        """Close and remove a child conversation.

        Args:
            parent_id: The ID of the parent conversation
            child_id: The ID of the child conversation to close
        """
        with self._registry_lock:
            # Verify parent-child relationship
            actual_parent_id = self._child_parent_map.get(child_id)
            if actual_parent_id != parent_id:
                logger.warning(
                    f"Child conversation {child_id} is not a child of {parent_id}"
                )
                return

            child = self._conversations.get(child_id)
            if child:
                # Close the child conversation
                child.close()

                # Update children.json mapping to remove the child
                parent = self._conversations.get(parent_id)
                if parent:
                    conversations_dir = os.path.join(
                        parent.state.workspace.working_dir, ".conversations"
                    )
                    parent_dir = os.path.join(conversations_dir, str(parent_id))
                    children_file = os.path.join(parent_dir, "children.json")

                    if os.path.exists(children_file):
                        with open(children_file) as f:
                            children_mapping = json.load(f)

                        # Remove child from mapping
                        children_mapping.pop(str(child_id), None)

                        with open(children_file, "w") as f:
                            json.dump(children_mapping, f, indent=2)

                # Unregister from global registry
                self.unregister(child_id)

                logger.info(f"Closed child conversation {child_id}")
            else:
                logger.warning(f"Child conversation {child_id} not found")

    def close_all_children(self, parent_id: ConversationID) -> None:
        """Close all child conversations of a parent.

        Args:
            parent_id: The ID of the parent conversation
        """
        with self._registry_lock:
            child_ids = self.get_child_ids(
                parent_id
            ).copy()  # Copy to avoid modification during iteration
            for child_id in child_ids:
                self.close_child_conversation(parent_id, child_id)
            logger.info(
                f"Closed all {len(child_ids)} child conversations for parent "
                f"{parent_id}"
            )

    def list_child_conversations(
        self, parent_id: ConversationID
    ) -> list[ConversationID]:
        """List all active child conversation IDs.

        Args:
            parent_id: The ID of the parent conversation

        Returns:
            List of child conversation IDs
        """
        return self.get_child_ids(parent_id)

    def get_children_mapping(
        self, parent_id: ConversationID
    ) -> dict[str, dict[str, str]]:
        """Get the children mapping from children.json file.

        Args:
            parent_id: The ID of the parent conversation

        Returns:
            Dictionary mapping child IDs to their metadata
        """
        with self._registry_lock:
            parent = self._conversations.get(parent_id)
            if parent is None:
                return {}

            conversations_dir = os.path.join(
                parent.state.workspace.working_dir, ".conversations"
            )
            parent_dir = os.path.join(conversations_dir, str(parent_id))
            children_file = os.path.join(parent_dir, "children.json")

            if os.path.exists(children_file):
                with open(children_file) as f:
                    return json.load(f)
            return {}

    def clear(self) -> None:
        """Clear all conversations from the registry. Used for testing."""
        with self._registry_lock:
            self._conversations.clear()
            self._parent_child_map.clear()
            self._child_parent_map.clear()
            logger.debug("ConversationRegistry cleared")


# Global registry instance
_global_registry: ConversationRegistry | None = None


def get_conversation_registry() -> ConversationRegistry:
    """Get the global conversation registry instance.

    Returns:
        The global ConversationRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ConversationRegistry()
    return _global_registry
