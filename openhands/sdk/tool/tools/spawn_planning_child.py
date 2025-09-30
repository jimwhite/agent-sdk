"""Tool for spawning a planning child conversation."""

from collections.abc import Sequence

from pydantic import Field
from rich.text import Text

from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool.tool import (
    ActionBase,
    ObservationBase,
    Tool,
    ToolAnnotations,
    ToolExecutor,
)


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
    error: str | None = Field(default=None, description="Error message if failed")

    @property
    def agent_observation(self) -> Sequence[TextContent | ImageContent]:
        if self.success:
            return [
                TextContent(
                    text=(
                        f"✅ {self.message}\n"
                        f"Child ID: {self.child_conversation_id}\n"
                        f"Working Directory: {self.working_directory}"
                    )
                )
            ]
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
    "Use this when you need to break down a complex task into a structured plan. "
    "The planning agent will analyze the task and create a PLAN.md file with "
    "detailed steps.\n\n"
    "The planning agent will:\n"
    "1. Analyze the task requirements\n"
    "2. Break down the task into specific steps\n"
    "3. Identify dependencies between steps\n"
    "4. Create a PLAN.md file with actionable instructions\n"
    "5. Consider risks and edge cases\n\n"
    "Use this tool when facing complex tasks that would benefit from structured "
    "planning before execution."
)


class SpawnPlanningChildExecutor(ToolExecutor):
    def __call__(
        self, action: SpawnPlanningChildAction
    ) -> SpawnPlanningChildObservation:
        from openhands.sdk.agent.registry import AgentRegistry

        # Get the current conversation from the tool's context
        conversation = getattr(self, "_conversation", None)
        if not conversation:
            return SpawnPlanningChildObservation(
                success=False,
                message="",
                error=(
                    "No active conversation found. This tool can only be used within a "
                    "conversation context."
                ),
            )

        try:
            # Create a planning agent
            registry = AgentRegistry()
            planning_agent = registry.create("planning", llm=conversation.agent.llm)

            # Create child conversation
            child_conversation = conversation.create_child_conversation(
                agent=planning_agent,
                visualize=False,
            )

            # Send the task description to the planning agent
            initial_message = (
                f"Please analyze the following task and create a detailed plan:\n\n"
                f"Task: {action.task_description}\n\n"
                f"Please create a PLAN.md file with:\n"
                f"1. Task breakdown into specific steps\n"
                f"2. Dependencies between steps\n"
                f"3. Expected outcomes for each step\n"
                f"4. Any risks or considerations\n\n"
                f"Focus on creating a clear, actionable plan that an execution agent "
                f"can follow."
            )

            # Send the initial message to the child conversation
            child_conversation.send_message(initial_message)

            return SpawnPlanningChildObservation(
                success=True,
                child_conversation_id=str(child_conversation._state.id),
                message=(
                    f"Created planning child conversation "
                    f"{child_conversation._state.id}. "
                    f"The planning agent will analyze the task and create a detailed "
                    f"plan."
                ),
                working_directory=child_conversation._state.working_dir,
            )

        except Exception as e:
            return SpawnPlanningChildObservation(
                success=False,
                message="",
                error=f"Failed to spawn planning child conversation: {str(e)}",
            )


SpawnPlanningChildTool = Tool(
    name="spawn_planning_child",
    description=SPAWN_PLANNING_CHILD_DESCRIPTION,
    action_type=SpawnPlanningChildAction,
    observation_type=SpawnPlanningChildObservation,
    executor=SpawnPlanningChildExecutor(),
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
