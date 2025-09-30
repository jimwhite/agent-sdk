"""Tool for writing implementation plans to PLAN.md."""

import os
from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk.tool import ActionBase, ObservationBase, Tool


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState


class WritePlanAction(ActionBase):
    """Action to write a plan to PLAN.md."""

    content: str = Field(description="The plan content to write to PLAN.md")

    @property
    def visualize(self) -> Text:
        """Visual representation of the action."""
        result = Text()
        result.append("📝 Writing plan to PLAN.md\n", style="bold cyan")
        result.append(f"Length: {len(self.content)} characters", style="white")
        return result


class WritePlanObservation(ObservationBase):
    """Observation from writing a plan."""

    success: bool = Field(description="Whether the plan was written successfully")
    file_path: str | None = Field(
        default=None, description="Path where the plan was written"
    )
    message: str = Field(description="Status message")

    @property
    def visualize(self) -> Text:
        """Visual representation of the observation."""
        content = Text()
        if self.success:
            content.append("✅ ", style="green bold")
            content.append("Plan written successfully\n", style="green")
            if self.file_path:
                content.append(f"Location: {self.file_path}\n", style="cyan")
        else:
            content.append("❌ ", style="red bold")
            content.append("Failed to write plan\n", style="red")
        content.append(self.message, style="white")
        return content


class WritePlanExecutor:
    """Executor for writing plans."""

    def __init__(self, state: "ConversationState"):
        self.state = state

    def __call__(self, action: WritePlanAction) -> WritePlanObservation:
        """Write the plan content to PLAN.md in the working directory."""
        try:
            # Write to working directory
            plan_path = os.path.join(self.state.working_dir, "PLAN.md")

            with open(plan_path, "w") as f:
                f.write(action.content)

            return WritePlanObservation(
                success=True,
                file_path=plan_path,
                message=f"Successfully wrote {len(action.content)} characters to PLAN.md",
            )
        except Exception as e:
            return WritePlanObservation(
                success=False,
                message=f"Error writing plan: {str(e)}",
            )


WritePlanTool = Tool(
    name="write_plan",
    action_type=WritePlanAction,
    observation_type=WritePlanObservation,
    executor_factory=WritePlanExecutor,
    description="Write an implementation plan to PLAN.md. Use this to document your research, analysis, and step-by-step implementation plan for complex tasks.",
)


__all__ = [
    "WritePlanAction",
    "WritePlanObservation",
    "WritePlanTool",
]
