"""Tool for executing a plan via an ExecutionAgent child conversation."""

import os
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool import (
    Action,
    Observation,
    ToolAnnotations,
    ToolBase,
    ToolDefinition,
    ToolExecutor,
)


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState


class ExecutePlanAction(Action):
    """Action for executing a plan via an ExecutionAgent child conversation."""

    plan_file: str = Field(
        default="PLAN.md", description="Path to the plan file (default: PLAN.md)"
    )

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation."""
        content = Text()
        content.append("⚡ ", style="yellow")
        content.append("Executing Plan: ", style="bold yellow")
        content.append(self.plan_file, style="white")
        return content


class ExecutePlanObservation(Observation):
    """Observation returned after executing a plan."""

    success: bool = Field(description="Whether the operation was successful")
    child_conversation_id: str | None = Field(
        default=None, description="ID of the created child conversation"
    )
    message: str = Field(description="Status message")
    working_directory: str | None = Field(
        default=None, description="Working directory of the child conversation"
    )
    plan_content: str | None = Field(
        default=None, description="Content of the plan file (truncated)"
    )
    error: str | None = Field(default=None, description="Error message if failed")

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        if self.success:
            return [
                TextContent(
                    text=(
                        f"SUCCESS: {self.message}\n"
                        f"Child ID: {self.child_conversation_id}\n"
                        f"Working Directory: {self.working_directory}"
                    )
                )
            ]
        else:
            return [TextContent(text=f"ERROR: {self.error}")]

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation."""
        content = Text()
        if self.success:
            content.append("SUCCESS: ", style="green")
            content.append(self.message, style="green")
            if self.child_conversation_id:
                content.append(f"\nChild ID: {self.child_conversation_id}", style="dim")
        else:
            content.append("ERROR: ", style="red")
            content.append(self.error or "Unknown error", style="red")
        return content


EXECUTE_PLAN_DESCRIPTION = (
    "Execute the plan by sending the content of PLAN.md back to the parent "
    "ExecutionAgent conversation. "
    "The parent ExecutionAgent will implement the plan step by step.\n\n"
    "This tool will:\n"
    "1. Read the specified plan file (default: PLAN.md)\n"
    "2. Send the plan content back to the parent ExecutionAgent conversation\n"
    "3. Close this planning child conversation\n\n"
    "The parent execution agent will then follow the plan sequence, verify each step, "
    "handle errors, and provide progress updates."
)


class ExecutePlanExecutor(ToolExecutor):
    def __init__(self, conversation_id: str | None = None):
        """Initialize the executor with conversation context."""
        self._conversation_id = conversation_id

    def __call__(self, action: ExecutePlanAction) -> ExecutePlanObservation:
        # Get the current conversation from the registry
        if self._conversation_id is None:
            return ExecutePlanObservation(
                success=False,
                message="",
                error=(
                    "No conversation ID provided. This tool can only be used within a "
                    "conversation context."
                ),
            )

        from uuid import UUID

        from openhands.sdk.conversation.registry import get_conversation_registry

        registry = get_conversation_registry()
        conversation = registry.get(UUID(self._conversation_id))
        if not conversation:
            return ExecutePlanObservation(
                success=False,
                message="",
                error=(
                    f"Conversation {self._conversation_id} not found in registry. "
                    "This tool can only be used within a conversation context."
                ),
            )

        # Cast to LocalConversation to access _state
        from typing import cast

        from openhands.sdk.conversation.impl.local_conversation import LocalConversation

        local_conversation = cast(LocalConversation, conversation)

        try:
            # Check if plan file exists
            plan_path = os.path.join(
                local_conversation._state.workspace.working_dir, action.plan_file
            )
            if not os.path.exists(plan_path):
                return ExecutePlanObservation(
                    success=False,
                    message="",
                    error=(
                        f"Plan file {action.plan_file} not found in "
                        f"{local_conversation._state.workspace.working_dir}"
                    ),
                )

            # Read the plan content
            with open(plan_path, encoding="utf-8") as f:
                plan_content = f.read()

            if not plan_content.strip():
                return ExecutePlanObservation(
                    success=False,
                    message="",
                    error=f"Plan file {action.plan_file} is empty",
                )

            # Get parent conversation
            parent_conversation = registry.get_parent_conversation(
                UUID(self._conversation_id)
            )
            if not parent_conversation:
                return ExecutePlanObservation(
                    success=False,
                    message="",
                    error="No parent conversation found. Cannot send plan back.",
                )

            # Send plan back to parent
            parent_message = (
                f"You can find the plan here: {plan_path}\n\n"
                f"Plan content:\n{plan_content}"
            )
            parent_conversation.send_message(parent_message)
            parent_conversation.run()

            # Mark task as complete before closing
            from openhands.sdk.agent.agents.planning.agent import PlanningAgent

            if isinstance(local_conversation.agent, PlanningAgent):
                local_conversation.agent.task_complete = True

            # Close this planning child conversation
            local_conversation.close()

            return ExecutePlanObservation(
                success=True,
                child_conversation_id=None,  # No child created
                message=(
                    "Plan sent back to parent conversation. "
                    "This planning conversation is closed. "
                    "The parent conversation will execute the plan."
                ),
                working_directory=plan_path,
                plan_content=plan_content[:500] + "..."
                if len(plan_content) > 500
                else plan_content,
            )

        except Exception as e:
            return ExecutePlanObservation(
                success=False, message="", error=f"Failed to execute plan: {str(e)}"
            )


class ExecutePlanTool(ToolBase):
    """Tool for executing a plan via an ExecutionAgent child conversation."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **params
    ) -> list[ToolBase[ExecutePlanAction, ExecutePlanObservation]]:
        """Create an ExecutePlanTool instance.

        Args:
            conv_state: The conversation state to get the conversation ID from
            **params: Additional parameters (not used)

        Returns:
            A list containing a single Tool instance.
        """
        conversation_id = str(conv_state.id)
        executor = ExecutePlanExecutor(conversation_id=conversation_id)

        tool = ToolDefinition(
            name="execute_plan",
            description=EXECUTE_PLAN_DESCRIPTION,
            action_type=ExecutePlanAction,
            observation_type=ExecutePlanObservation,
            executor=executor,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
        )
        return [tool]
