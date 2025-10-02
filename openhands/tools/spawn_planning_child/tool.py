"""Spawn Planning Child Tool - Direct tool for ExecutionAgent to call PlanningAgent."""

import time
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from pydantic import Field
from rich.text import Text

from openhands.sdk.agent.registry import AgentRegistry
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.conversation.registry import get_conversation_registry
from openhands.sdk.llm.message import TextContent
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import (
    Action,
    Observation,
    ToolAnnotations,
    ToolDefinition,
    ToolExecutor,
)


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState

logger = get_logger(__name__)


def wait_for_task_completion(
    child_conversation: LocalConversation, timeout: int = 300
) -> bool:
    """Wait for a child conversation's agent to complete its task.

    Args:
        child_conversation: The child conversation to monitor
        timeout: Maximum time to wait in seconds (default: 5 minutes)

    Returns:
        True if task completed successfully, False if timeout or error
    """
    start_time = time.time()

    while time.time() - start_time < timeout:
        # Check if agent has task_complete attribute and if it's True
        if hasattr(child_conversation.agent, "task_complete") and getattr(
            child_conversation.agent, "task_complete", False
        ):
            return True

        # Wait 1 second before checking again
        time.sleep(1)

    # Timeout reached
    return False


class SpawnPlanningChildAction(Action):
    """Action for spawning a planning child conversation."""

    task_description: str = Field(
        description="Description of the task for the planning child agent"
    )

    @property
    def to_llm_content(self) -> list[TextContent]:
        """Get the action content to show to the agent."""
        content = Text()
        content.append("Spawning planning child with task: ", style="bold blue")
        content.append(
            self.task_description[:100] + "..."
            if len(self.task_description) > 100
            else self.task_description,
            style="white",
        )
        return [TextContent(text=str(content))]


class SpawnPlanningChildObservation(Observation):
    """Observation returned after spawning a planning child conversation."""

    success: bool = Field(description="Whether the spawn operation was successful")
    child_conversation_id: str | None = Field(
        default=None, description="ID of the spawned child conversation"
    )
    working_directory: str | None = Field(
        default=None, description="Working directory of the parent conversation"
    )
    error: str | None = Field(default=None, description="Error message if spawn failed")
    message: str = Field(description="Human-readable message about the spawn operation")

    @property
    def to_llm_content(self) -> list[TextContent]:
        """Get the observation content to show to the agent."""
        if self.success:
            return [
                TextContent(
                    text=(
                        f"Planning child spawned with ID: "
                        f"{self.child_conversation_id}. {self.message}"
                    )
                )
            ]
        else:
            return [TextContent(text=f"Failed to spawn planning child: {self.error}")]

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation."""
        content = Text()
        if self.success:
            content.append("Planning child spawned: ", style="bold green")
            content.append(f"{self.child_conversation_id}", style="cyan")
        else:
            content.append("Failed to spawn planning child: ", style="bold red")
            content.append(f"{self.error}", style="red")
        return content


class SpawnPlanningChildExecutor(ToolExecutor):
    """Executor for spawning planning child conversations."""

    def __init__(self, conversation_state: "ConversationState"):
        """Initialize the executor with conversation state."""
        self._conversation_id = conversation_state.id if conversation_state else None

    def __call__(
        self, action: SpawnPlanningChildAction
    ) -> SpawnPlanningChildObservation:
        """Execute the spawn planning child action.

        Args:
            action: The spawn planning child action to execute

        Returns:
            SpawnPlanningChildObservation: Result of the spawn operation
        """
        try:
            if self._conversation_id is None:
                return SpawnPlanningChildObservation(
                    success=False,
                    error="No conversation ID provided",
                    message="No conversation ID provided",
                )

            # Get the parent conversation
            conversation_registry = get_conversation_registry()
            parent_conversation = conversation_registry.get(self._conversation_id)

            if parent_conversation is None:
                return SpawnPlanningChildObservation(
                    success=False,
                    error=(
                        f"Parent conversation {self._conversation_id} "
                        f"not found in registry"
                    ),
                    message=(
                        f"Parent conversation {self._conversation_id} "
                        f"not found in registry"
                    ),
                )

            # Use parent agent's LLM for child agent
            parent_local_conv = cast(LocalConversation, parent_conversation)
            child_llm = parent_local_conv.agent.llm

            # Create the planning child agent
            agent_registry = AgentRegistry()
            child_agent = agent_registry.create(
                name="planning",  # Always use "planning" agent type
                llm=child_llm,
            )

            # Create child conversation
            child_conversation = conversation_registry.create_child_conversation(
                parent_id=self._conversation_id,
                agent=child_agent,
                task_description=action.task_description,
            )

            child_local_conv = cast(LocalConversation, child_conversation)

            return SpawnPlanningChildObservation(
                success=True,
                child_conversation_id=str(child_local_conv._state.id),
                working_directory=parent_local_conv._state.workspace.working_dir,
                message=(
                    "Planning child created successfully. "
                    "User can now send messages to it."
                ),
            )

        except Exception as e:
            logger.exception("Failed to spawn planning child")
            return SpawnPlanningChildObservation(
                success=False,
                error=str(e),
                message=f"Failed to create planning child: {str(e)}",
            )


# Tool definition with detailed description
SPAWN_PLANNING_CHILD_DESCRIPTION = """Spawn a child planning agent.

This tool creates a planning child conversation that can be used to break down
complex tasks into manageable steps. The planning agent will create detailed
plans and can call execute_plan to return control to the parent execution agent.

Key features:
- Creates a PlanningAgent child conversation
- Uses the same LLM as the parent agent
- Returns immediately after creating the child (non-blocking)
- User must send messages directly to the child conversation
- Planning agent can create PLAN.md files and call execute_plan tool

Usage:
1. ExecutionAgent calls this tool with a task description
2. Tool creates a PlanningAgent child conversation
3. User sends messages to the planning child to create plans
4. Planning child creates PLAN.md and calls execute_plan when ready
5. Control returns to the parent ExecutionAgent for implementation

This tool eliminates the need for generic agent dispatchers and provides a
direct, focused solution for planning delegation."""


spawn_planning_child_tool = ToolDefinition(
    name="spawn_planning_child",
    description=SPAWN_PLANNING_CHILD_DESCRIPTION,
    action_type=SpawnPlanningChildAction,
    observation_type=SpawnPlanningChildObservation,
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)


class SpawnPlanningChildTool(
    ToolDefinition[SpawnPlanningChildAction, SpawnPlanningChildObservation]
):
    """A ToolDefinition subclass that initializes a SpawnPlanningChildExecutor."""

    @classmethod
    def create(
        cls, conv_state: "ConversationState"
    ) -> Sequence["SpawnPlanningChildTool"]:
        """Initialize SpawnPlanningChildTool with a SpawnPlanningChildExecutor.

        Args:
            conv_state: Conversation state to get the conversation ID from
        """
        executor = SpawnPlanningChildExecutor(conv_state)

        # Initialize the parent Tool with the executor
        return [
            cls(
                name="spawn_planning_child",
                description=SPAWN_PLANNING_CHILD_DESCRIPTION,
                action_type=SpawnPlanningChildAction,
                observation_type=SpawnPlanningChildObservation,
                annotations=spawn_planning_child_tool.annotations,
                executor=executor,
            )
        ]
