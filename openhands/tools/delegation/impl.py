"""Implementation of delegation tool executor."""

from typing import TYPE_CHECKING

from openhands.sdk.delegation.manager import DelegationManager
from openhands.sdk.logger import get_logger
from openhands.sdk.tool.tool import ToolExecutor
from openhands.tools.preset.worker import get_worker_agent

if TYPE_CHECKING:
    from openhands.tools.delegation.definition import DelegateAction, DelegateObservation

logger = get_logger(__name__)


class DelegateExecutor(ToolExecutor):
    """Executor for delegation operations."""

    def __init__(self):
        self.delegation_manager = DelegationManager()

    def __call__(self, action: "DelegateAction") -> "DelegateObservation":
        """Execute a delegation action."""
        from openhands.tools.delegation.definition import DelegateObservation
        
        if action.operation == "spawn":
            return self._spawn_sub_agent(action)
        elif action.operation == "send":
            return self._send_to_sub_agent(action)
        elif action.operation == "status":
            return self._get_sub_agent_status(action)
        elif action.operation == "close":
            return self._close_sub_agent(action)
        else:
            return DelegateObservation(
                status="error",
                message=f"Unknown operation: {action.operation}"
            )

    def _spawn_sub_agent(self, action: "DelegateAction") -> "DelegateObservation":
        """Spawn a new sub-agent."""
        from openhands.tools.delegation.definition import DelegateObservation
        
        if not action.task:
            return DelegateObservation(
                status="error",
                message="Task is required for spawn operation"
            )

        try:
            # Get the parent conversation from the current context
            # This is a bit tricky - we need to access the current conversation
            # For now, we'll store it when the executor is created
            parent_conversation = getattr(self, '_parent_conversation', None)
            if parent_conversation is None:
                return DelegateObservation(
                    status="error",
                    message="No parent conversation available for delegation"
                )

            # Create worker agent with same LLM as parent
            parent_llm = parent_conversation.state.agent.llm
            worker_agent = get_worker_agent(llm=parent_llm)

            # Spawn the sub-agent
            sub_conversation = self.delegation_manager.spawn_sub_agent(
                parent_conversation=parent_conversation,
                task=action.task,
                worker_agent=worker_agent,
            )

            return DelegateObservation(
                sub_conversation_id=sub_conversation.id,
                status="created",
                message=f"Sub-agent created successfully with ID: {sub_conversation.id}",
                result=f"Task assigned: {action.task}"
            )

        except Exception as e:
            logger.error(f"Failed to spawn sub-agent: {e}")
            return DelegateObservation(
                status="error",
                message=f"Failed to spawn sub-agent: {str(e)}"
            )

    def _send_to_sub_agent(self, action: "DelegateAction") -> "DelegateObservation":
        """Send a message to a sub-agent."""
        from openhands.tools.delegation.definition import DelegateObservation
        
        if not action.sub_conversation_id:
            return DelegateObservation(
                status="error",
                message="Sub-conversation ID is required for send operation"
            )

        if not action.message:
            return DelegateObservation(
                status="error",
                message="Message is required for send operation"
            )

        success = self.delegation_manager.send_to_sub_agent(
            sub_conversation_id=action.sub_conversation_id,
            message=action.message
        )

        if success:
            return DelegateObservation(
                sub_conversation_id=action.sub_conversation_id,
                status="message_sent",
                message=f"Message sent to sub-agent {action.sub_conversation_id}",
                result=f"Message: {action.message}"
            )
        else:
            return DelegateObservation(
                sub_conversation_id=action.sub_conversation_id,
                status="error",
                message=f"Failed to send message to sub-agent {action.sub_conversation_id}"
            )

    def _get_sub_agent_status(self, action: "DelegateAction") -> "DelegateObservation":
        """Get the status of a sub-agent."""
        from openhands.tools.delegation.definition import DelegateObservation
        
        if not action.sub_conversation_id:
            return DelegateObservation(
                status="error",
                message="Sub-conversation ID is required for status operation"
            )

        # Check if sub-agent exists
        if action.sub_conversation_id not in self.delegation_manager.conversations:
            return DelegateObservation(
                sub_conversation_id=action.sub_conversation_id,
                status="not_found",
                message=f"Sub-agent {action.sub_conversation_id} not found"
            )

        # Get sub-conversation and check its status
        sub_conversation = self.delegation_manager.conversations[action.sub_conversation_id]
        agent_status = sub_conversation.state.agent_status

        return DelegateObservation(
            sub_conversation_id=action.sub_conversation_id,
            status="active",
            message=f"Sub-agent {action.sub_conversation_id} is {agent_status.value}",
            result=f"Agent status: {agent_status.value}"
        )

    def _close_sub_agent(self, action: "DelegateAction") -> "DelegateObservation":
        """Close a sub-agent."""
        from openhands.tools.delegation.definition import DelegateObservation
        
        if not action.sub_conversation_id:
            return DelegateObservation(
                status="error",
                message="Sub-conversation ID is required for close operation"
            )

        success = self.delegation_manager.close_sub_agent(
            sub_conversation_id=action.sub_conversation_id
        )

        if success:
            return DelegateObservation(
                sub_conversation_id=action.sub_conversation_id,
                status="closed",
                message=f"Sub-agent {action.sub_conversation_id} closed successfully"
            )
        else:
            return DelegateObservation(
                sub_conversation_id=action.sub_conversation_id,
                status="error",
                message=f"Failed to close sub-agent {action.sub_conversation_id}"
            )

    def set_parent_conversation(self, conversation):
        """Set the parent conversation for this executor."""
        self._parent_conversation = conversation