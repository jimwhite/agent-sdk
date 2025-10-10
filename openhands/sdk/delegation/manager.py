"""DelegationManager for handling agent delegation and message routing."""

import uuid
from typing import TYPE_CHECKING

from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.logger import get_logger

if TYPE_CHECKING:
    from openhands.sdk.agent.base import AgentBase
    from openhands.sdk.conversation.base import BaseConversation

logger = get_logger(__name__)


class DelegationManager:
    """Manages agent delegation relationships and message routing.
    
    This class handles:
    - Creating sub-agents and their conversations
    - Tracking parent-child relationships in memory
    - Routing messages between parent and child agents
    - Managing sub-agent lifecycle
    """

    def __init__(self):
        # Store conversation references to prevent garbage collection
        self.conversations: dict[str, "BaseConversation"] = {}
        # Track parent-child relationships
        self.parent_to_children: dict[str, set[str]] = {}
        self.child_to_parent: dict[str, str] = {}

    def spawn_sub_agent(
        self,
        parent_conversation: "BaseConversation",
        task: str,
        worker_agent: "AgentBase",
    ) -> "BaseConversation":
        """Spawn a sub-agent with a new conversation.
        
        Args:
            parent_conversation: The parent conversation
            task: The task description for the sub-agent
            worker_agent: The worker agent to use for the sub-conversation
            
        Returns:
            The new sub-conversation
        """
        from openhands.sdk.conversation import Conversation
        
        # Create a unique ID for the sub-conversation
        sub_conversation_id = str(uuid.uuid4())
        
        # Create sub-conversation with shared workspace
        sub_conversation = Conversation(
            agent=worker_agent,
            workspace=parent_conversation.state.workspace,
            conversation_id=sub_conversation_id,
            # Don't persist sub-conversations to avoid conflicts
            persistence_dir=None,
            # Add custom callback to route messages to parent
            callbacks=[self._create_message_router(parent_conversation)],
            # Disable visualization for sub-agents to avoid conflicts
            visualize=False,
        )
        
        # Store conversation reference
        self.conversations[sub_conversation_id] = sub_conversation
        
        # Track relationships
        parent_id = parent_conversation.id
        if parent_id not in self.parent_to_children:
            self.parent_to_children[parent_id] = set()
        self.parent_to_children[parent_id].add(sub_conversation_id)
        self.child_to_parent[sub_conversation_id] = parent_id
        
        # Send initial task to sub-agent
        sub_conversation.send_message(task)
        
        logger.info(
            f"Spawned sub-agent {sub_conversation_id} for parent {parent_id} "
            f"with task: {task[:100]}..."
        )
        
        return sub_conversation

    def send_to_sub_agent(
        self,
        sub_conversation_id: str,
        message: str
    ) -> bool:
        """Send a message to a sub-agent.
        
        Args:
            sub_conversation_id: ID of the sub-conversation
            message: Message to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        sub_conversation = self.conversations.get(sub_conversation_id)
        if sub_conversation is None:
            logger.error(f"Sub-conversation {sub_conversation_id} not found")
            return False
            
        try:
            sub_conversation.send_message(message)
            logger.debug(f"Sent message to sub-agent {sub_conversation_id}: {message[:100]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to sub-agent {sub_conversation_id}: {e}")
            return False

    def close_sub_agent(
        self,
        sub_conversation_id: str
    ) -> bool:
        """Close a sub-agent and clean up resources.
        
        Args:
            sub_conversation_id: ID of the sub-conversation to close
            
        Returns:
            True if closed successfully, False otherwise
        """
        if sub_conversation_id not in self.conversations:
            logger.error(f"Sub-conversation {sub_conversation_id} not found")
            return False
            
        try:
            # Get parent ID before cleanup
            parent_id = self.child_to_parent.get(sub_conversation_id)
            
            # Clean up relationships
            if parent_id and parent_id in self.parent_to_children:
                self.parent_to_children[parent_id].discard(sub_conversation_id)
                if not self.parent_to_children[parent_id]:
                    del self.parent_to_children[parent_id]
            
            if sub_conversation_id in self.child_to_parent:
                del self.child_to_parent[sub_conversation_id]
            
            # Remove conversation reference
            del self.conversations[sub_conversation_id]
            
            logger.info(f"Closed sub-agent {sub_conversation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to close sub-agent {sub_conversation_id}: {e}")
            return False

    def get_sub_agents(self, parent_conversation_id: str) -> list[str]:
        """Get list of sub-agent IDs for a parent conversation.
        
        Args:
            parent_conversation_id: ID of the parent conversation
            
        Returns:
            List of sub-agent conversation IDs
        """
        return list(self.parent_to_children.get(parent_conversation_id, set()))

    def is_sub_agent(self, conversation_id: str) -> bool:
        """Check if a conversation is a sub-agent.
        
        Args:
            conversation_id: ID of the conversation to check
            
        Returns:
            True if it's a sub-agent, False otherwise
        """
        return conversation_id in self.child_to_parent

    def get_parent_id(self, sub_conversation_id: str) -> str | None:
        """Get the parent conversation ID for a sub-agent.
        
        Args:
            sub_conversation_id: ID of the sub-conversation
            
        Returns:
            Parent conversation ID or None if not found
        """
        return self.child_to_parent.get(sub_conversation_id)

    def _create_message_router(self, parent_conversation: "BaseConversation"):
        """Create a callback function that routes sub-agent messages to parent.
        
        Args:
            parent_conversation: The parent conversation to route messages to
            
        Returns:
            Callback function for message routing
        """
        def route_message_to_parent(event):
            # Only route MessageEvents from the agent (not user messages)
            from openhands.sdk.event import MessageEvent
            
            if isinstance(event, MessageEvent) and event.source == "agent":
                # Extract the message content
                message_content = ""
                if event.llm_message and event.llm_message.content:
                    from openhands.sdk.llm.message import TextContent
                    text_contents = [
                        c for c in event.llm_message.content 
                        if isinstance(c, TextContent)
                    ]
                    if text_contents:
                        message_content = "\n".join(c.text for c in text_contents)
                
                if message_content:
                    # Route the message to the parent conversation
                    try:
                        parent_conversation.send_message(
                            f"Sub-agent response: {message_content}"
                        )
                        logger.debug(
                            f"Routed message from sub-agent to parent: "
                            f"{message_content[:100]}..."
                        )
                    except Exception as e:
                        logger.error(f"Failed to route message to parent: {e}")
        
        return route_message_to_parent