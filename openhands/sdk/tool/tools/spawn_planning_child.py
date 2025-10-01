"""Tool for spawning a planning child conversation using AgentDispatcher."""

import os
from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool.tool import (
    Tool,
    ToolAnnotations,
    ToolBase,
)
from openhands.sdk.tool.tools.agent_dispatcher import (
    AgentDispatcher,
    SpawnChildAction,
    SpawnChildObservation,
)


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState


class SpawnPlanningChildAction(SpawnChildAction):
    """Action for spawning a planning child conversation."""

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


class SpawnPlanningChildObservation(SpawnChildObservation):
    """Observation returned after spawning a planning child conversation."""

    plan_file_path: str | None = Field(
        default=None, description="Path to the generated PLAN.md file"
    )

    @property
    def agent_observation(self) -> Sequence[TextContent | ImageContent]:
        if self.success:
            text_parts = [
                f"✅ {self.message}",
                f"Child ID: {self.child_conversation_id}",
                f"Agent Type: {self.agent_type}",
                f"Working Directory: {self.working_directory}",
            ]
            if self.plan_file_path:
                text_parts.append(f"Plan File: {self.plan_file_path}")
            return [TextContent(text="\n".join(text_parts))]
        else:
            return [TextContent(text=f"❌ {self.error}")]


class SpawnPlanningChildTool(ToolBase):
    """Tool for spawning a planning child conversation using AgentDispatcher."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState", **params
    ) -> list[Tool[SpawnPlanningChildAction, SpawnPlanningChildObservation]]:
        """Create a SpawnPlanningChildTool instance using AgentDispatcher.

        Args:
            conv_state: The conversation state containing the conversation ID
            **params: Additional parameters (not used)

        Returns:
            A list containing a single Tool instance.
        """
        dispatcher = AgentDispatcher()

        # Create the base tool using the dispatcher
        base_tool = dispatcher.create_spawn_tool("planning", conv_state)

        # Create a custom executor that adds plan file path information
        class PlanningChildExecutor:
            def __init__(self, base_executor):
                self._base_executor = base_executor

            def __call__(
                self, action: SpawnPlanningChildAction
            ) -> SpawnPlanningChildObservation:
                # Call the base executor
                base_result = self._base_executor(action)

                # Convert to planning-specific observation with plan file path
                plan_file_path = None
                if base_result.success and base_result.working_directory:
                    potential_plan_path = os.path.join(
                        base_result.working_directory, "PLAN.md"
                    )
                    if os.path.exists(potential_plan_path):
                        plan_file_path = potential_plan_path

                return SpawnPlanningChildObservation(
                    success=base_result.success,
                    child_conversation_id=base_result.child_conversation_id,
                    message=base_result.message,
                    working_directory=base_result.working_directory,
                    agent_type=base_result.agent_type,
                    error=base_result.error,
                    plan_file_path=plan_file_path,
                )

        # Create the enhanced tool
        enhanced_executor = PlanningChildExecutor(base_tool.executor)

        tool = Tool(
            name="spawn_planning_child",
            description=base_tool.description,
            action_type=SpawnPlanningChildAction,
            observation_type=SpawnPlanningChildObservation,
            executor=enhanced_executor,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
        )
        return [tool]
