"""Tool for spawning a planning child conversation."""

import os
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk.agent.registry import AgentRegistry
from openhands.sdk.conversation.registry import get_conversation_registry
from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool.tool import (
    ActionBase,
    ObservationBase,
    Tool,
    ToolAnnotations,
    ToolBase,
    ToolExecutor,
)


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState


class SpawnPlanningChildAction(ActionBase):
    """Action for spawning a planning child conversation."""

    task_description: str = Field(
        description="Description of the task that needs planning"
    )

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation."""
        content = Text()
        content.append("🧠 ", style="blue")
        content.append("Spawning Planning Child: ", style="bold blue")
        content.append(
            self.task_description[:100] + "..."
            if len(self.task_description) > 100
            else self.task_description,
            style="white",
        )
        return content


class SpawnPlanningChildObservation(ObservationBase):
    """Observation returned after spawning a planning child conversation."""

    success: bool = Field(description="Whether the operation was successful")
    child_conversation_id: str | None = Field(
        default=None, description="ID of the created child conversation"
    )
    message: str = Field(description="Status message")
    working_directory: str | None = Field(
        default=None, description="Working directory of the child conversation"
    )
    plan_file_path: str | None = Field(
        default=None, description="Path to the generated PLAN.md file"
    )
    error: str | None = Field(default=None, description="Error message if failed")

    @property
    def agent_observation(self) -> Sequence[TextContent | ImageContent]:
        if self.success:
            text_parts = [
                f"✅ {self.message}",
                f"Child ID: {self.child_conversation_id}",
                f"Working Directory: {self.working_directory}",
            ]
            if self.plan_file_path:
                text_parts.append(f"Plan File: {self.plan_file_path}")
            return [TextContent(text="\n".join(text_parts))]
        else:
            return [TextContent(text=f"❌ {self.error}")]

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation."""
        content = Text()
        if self.success:
            content.append("✅ ", style="green")
            content.append(self.message, style="green")
            if self.child_conversation_id:
                content.append(f"\nChild ID: {self.child_conversation_id}", style="dim")
        else:
            content.append("❌ ", style="red")
            content.append(self.error or "Unknown error", style="red")
        return content


SPAWN_PLANNING_CHILD_DESCRIPTION = (
    "Spawn a child conversation with a PlanningAgent to create a detailed plan. "
    "This tool is non-BLOCKING."
    "Use this when you need to break down a complex task into a structured plan.\n\n"
    "The tool will:\n"
    "1. Create a PlanningAgent child conversation\n"
    "3. Return an observation.\n"
    "The planning agent will analyze requirements, break down tasks into steps, "
    "identify dependencies, and create actionable instructions."
)


class SpawnPlanningChildExecutor(ToolExecutor):
    def __init__(self, conversation_id: ConversationID | None = None):
        """Initialize the executor with conversation ID."""
        self._conversation_id = conversation_id

    def __call__(
        self, action: SpawnPlanningChildAction
    ) -> SpawnPlanningChildObservation:
        # Get the current conversation from the global registry
        if not self._conversation_id:
            return SpawnPlanningChildObservation(
                success=False,
                message="",
                error=(
                    "No conversation ID provided. This tool can only be used within a "
                    "conversation context."
                ),
            )

        registry = get_conversation_registry()
        conversation = registry.get(self._conversation_id)
        if not conversation:
            return SpawnPlanningChildObservation(
                success=False,
                message="",
                error=(f"Conversation {self._conversation_id} not found in registry."),
            )

        try:
            # Get working directory from parent conversation before creating child
            working_dir = conversation._state.workspace.working_dir

            registry = AgentRegistry()
            planning_agent = registry.create(
                "planning",
                llm=conversation.agent.llm,
                system_prompt_kwargs={"WORK_DIR": working_dir},
            )

            # Create child conversation directly through registry
            conv_registry = get_conversation_registry()
            child_conversation = conv_registry.create_child_conversation(
                parent_id=conversation._state.id,
                agent=planning_agent,
                visualize=True,  # Disable visualization to avoid I/O blocking issues
            )
            plan_file_path = os.path.join(working_dir, "PLAN.md")

            return SpawnPlanningChildObservation(
                success=True,
                child_conversation_id=str(child_conversation._state.id),
                message=("Planning child created."),
                working_directory=working_dir,
                plan_file_path=plan_file_path
                if os.path.exists(plan_file_path)
                else None,
            )

        except Exception as e:
            return SpawnPlanningChildObservation(
                success=False,
                message="",
                error=f"Failed to spawn planning child: {str(e)}",
            )


class SpawnPlanningChildTool(ToolBase):
    """Tool for spawning a planning child conversation."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **params
    ) -> list[Tool[SpawnPlanningChildAction, SpawnPlanningChildObservation]]:
        """Create a SpawnPlanningChildTool instance.

        Args:
            conv_state: The conversation state containing the conversation ID
            **params: Additional parameters (not used)

        Returns:
            A list containing a single Tool instance.
        """
        executor = SpawnPlanningChildExecutor(conversation_id=conv_state.id)

        tool = Tool(
            name="spawn_planning_child",
            description=SPAWN_PLANNING_CHILD_DESCRIPTION,
            action_type=SpawnPlanningChildAction,
            observation_type=SpawnPlanningChildObservation,
            executor=executor,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
        )
        return [tool]
