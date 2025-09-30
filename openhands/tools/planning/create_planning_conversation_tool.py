"""Tool for creating planning conversations with child agents."""

from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk.agent.registry import AgentRegistry
from openhands.sdk.tool import ActionBase, ObservationBase, Tool


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState


class CreatePlanningConversationAction(ActionBase):
    """Action to create a child planning conversation."""

    task_description: str = Field(
        description="Description of the task for the planning agent to research and plan"
    )

    @property
    def visualize(self) -> Text:
        """Visual representation of the action."""
        content = Text()
        content.append("🎯 Creating planning conversation\n", style="bold cyan")
        content.append(f"Task: {self.task_description}", style="white")
        return content


class CreatePlanningConversationObservation(ObservationBase):
    """Observation from creating a planning conversation."""

    success: bool = Field(
        description="Whether the conversation was created successfully"
    )
    conversation_id: str | None = Field(
        default=None, description="ID of the created child conversation"
    )
    message: str = Field(description="Status message")

    @property
    def visualize(self) -> Text:
        """Visual representation of the observation."""
        content = Text()
        if self.success:
            content.append("✅ ", style="green bold")
            content.append("Planning conversation created\n", style="green")
            if self.conversation_id:
                content.append(f"ID: {self.conversation_id}\n", style="cyan")
        else:
            content.append("❌ ", style="red bold")
            content.append("Failed to create planning conversation\n", style="red")
        content.append(self.message, style="white")
        return content


class CreatePlanningConversationExecutor:
    """Executor for creating planning conversations."""

    def __init__(self, state: "ConversationState"):
        self.state = state

    def __call__(
        self, action: CreatePlanningConversationAction
    ) -> CreatePlanningConversationObservation:
        """Create a child conversation with a planning agent."""
        # Access parent conversation via weak reference
        conversation = self.state.conversation
        if conversation is None:
            return CreatePlanningConversationObservation(
                success=False,
                message="Conversation reference not available in state",
            )

        try:
            # Create planning agent using registry
            planning_llm = self.state.agent.llm
            planning_agent = AgentRegistry.create("planning", llm=planning_llm)

            # Create child conversation
            child_conversation = conversation.create_child_conversation(
                agent=planning_agent
            )

            # Send task to planning agent
            child_conversation.send_message(action.task_description)

            # Run the planning conversation
            child_conversation.run()

            return CreatePlanningConversationObservation(
                success=True,
                conversation_id=str(child_conversation.id),
                message=f"Successfully created planning conversation and sent task. The planning agent will research and create a plan in PLAN.md in its working directory: {child_conversation.state.working_dir}",
            )
        except Exception as e:
            return CreatePlanningConversationObservation(
                success=False,
                message=f"Error creating planning conversation: {str(e)}",
            )


CreatePlanningConversationTool = Tool(
    name="create_planning_conversation",
    action_type=CreatePlanningConversationAction,
    observation_type=CreatePlanningConversationObservation,
    executor_factory=CreatePlanningConversationExecutor,
    description="Create a child conversation with a planning agent to research a complex task and create a detailed implementation plan. The planning agent will analyze the codebase, understand dependencies, and write a comprehensive plan to PLAN.md.",
)


__all__ = [
    "CreatePlanningConversationAction",
    "CreatePlanningConversationObservation",
    "CreatePlanningConversationTool",
]
