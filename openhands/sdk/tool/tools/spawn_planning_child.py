"""Tool for spawning a planning child conversation."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

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
    "This tool BLOCKS until the planning is complete and returns the path to PLAN.md. "
    "Use this when you need to break down a complex task into a structured plan.\n\n"
    "The tool will:\n"
    "1. Create a PlanningAgent child conversation\n"
    "2. Send the task description to the planning agent\n"
    "3. Wait for the planning agent to create a PLAN.md file\n"
    "4. Wait for the planning agent to call execute_plan tool\n"
    "5. Return the path to the generated PLAN.md file\n\n"
    "The planning agent will analyze requirements, break down tasks into steps, "
    "identify dependencies, and create actionable instructions. This tool provides "
    "synchronous planning - it will not return until planning is complete."
)


class SpawnPlanningChildExecutor(ToolExecutor):
    def __init__(self):
        """Initialize the executor with no conversation context."""
        self._conversation = None

    def __call__(
        self, action: SpawnPlanningChildAction
    ) -> SpawnPlanningChildObservation:
        import os
        from openhands.sdk.agent.registry import AgentRegistry

        # Get the current conversation from the tool's context
        conversation = self._conversation
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
                visualize=True,  # Enable visualization to see child's logs
            )

            # Send the task description to the planning agent
            planning_message = (
                f"Please create a detailed plan for the following task:\n\n"
                f"{action.task_description}\n\n"
                f"Create a PLAN.md file with specific, actionable steps. "
                f"When you're done planning, use the execute_plan tool to execute the plan."
            )
            
            child_conversation.send_message(planning_message)
            
            # Run the child conversation until it calls execute_plan
            # The execute_plan tool will send the plan back to this parent conversation
            # and close the child conversation
            child_conversation.run()
            
            # After the child runs and calls execute_plan, look for PLAN.md
            working_dir = child_conversation._state.workspace.working_dir
            plan_file_path = os.path.join(working_dir, "PLAN.md")
            
            if os.path.exists(plan_file_path):
                return SpawnPlanningChildObservation(
                    success=True,
                    child_conversation_id=str(child_conversation._state.id),
                    message=(
                        f"Planning completed successfully. "
                        f"Child conversation {child_conversation._state.id} created a plan "
                        f"and called execute_plan. The plan is ready for execution."
                    ),
                    working_directory=working_dir,
                    plan_file_path=plan_file_path,
                )
            else:
                return SpawnPlanningChildObservation(
                    success=False,
                    message="",
                    error=(
                        f"Planning child completed but no PLAN.md file was found at "
                        f"{plan_file_path}. The planning agent may not have created the plan."
                    ),
                )

        except Exception as e:
            return SpawnPlanningChildObservation(
                success=False,
                message="",
                error=f"Failed to complete planning: {str(e)}",
            )


class SpawnPlanningChildTool(ToolBase):
    """Tool for spawning a planning child conversation."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **params
    ) -> list["SpawnPlanningChildTool"]:
        """Create a SpawnPlanningChildTool instance.

        Note: The conversation context will be injected by LocalConversation
        after tool initialization.

        Args:
            conv_state: The conversation state (not used but required by protocol)
            **params: Additional parameters (not used)

        Returns:
            A list containing a single Tool instance.
        """
        executor = SpawnPlanningChildExecutor()

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
