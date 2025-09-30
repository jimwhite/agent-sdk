"""Tool for executing a plan via an ExecutionAgent child conversation."""

import os
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


class ExecutePlanAction(ActionBase):
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


class ExecutePlanObservation(ObservationBase):
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


EXECUTE_PLAN_DESCRIPTION = (
    "Execute the plan by sending the content of PLAN.md to a new ExecutionAgent "
    "child conversation. "
    "The ExecutionAgent will implement the plan step by step.\n\n"
    "This tool will:\n"
    "1. Read the specified plan file (default: PLAN.md)\n"
    "2. Create an ExecutionAgent child conversation\n"
    "3. Send the plan content to the execution agent\n"
    "4. Let the execution agent implement the plan step by step\n\n"
    "The execution agent will follow the plan sequence, verify each step, "
    "handle errors, and provide progress updates."
)


class ExecutePlanExecutor(ToolExecutor):
    def __call__(self, action: ExecutePlanAction) -> ExecutePlanObservation:
        from openhands.sdk.agent.registry import AgentRegistry

        # Get the current conversation from the tool's context
        conversation = getattr(self, "_conversation", None)
        if not conversation:
            return ExecutePlanObservation(
                success=False,
                message="",
                error=(
                    "No active conversation found. This tool can only be used within a "
                    "conversation context."
                ),
            )

        try:
            # Check if plan file exists
            plan_path = os.path.join(conversation._state.working_dir, action.plan_file)
            if not os.path.exists(plan_path):
                return ExecutePlanObservation(
                    success=False,
                    message="",
                    error=(
                        f"Plan file {action.plan_file} not found in "
                        f"{conversation._state.working_dir}"
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

            # Create an execution agent
            registry = AgentRegistry()
            execution_agent = registry.create("execution", llm=conversation.agent.llm)

            # Create child conversation
            child_conversation = conversation.create_child_conversation(
                agent=execution_agent,
                visualize=False,
            )

            # Send the plan to the execution agent
            execution_message = f"""Please implement the following plan step by step:

{plan_content}

Execute each step carefully and provide updates on your progress. Make sure to:
1. Follow the plan sequence
2. Verify each step is completed successfully
3. Handle any errors or issues that arise
4. Provide a summary when all steps are complete"""

            # Send the execution message to the child conversation
            child_conversation.send_message(execution_message)

            child_id = str(child_conversation._state.id)
            working_dir = child_conversation._state.working_dir

            return ExecutePlanObservation(
                success=True,
                child_conversation_id=child_id,
                message=(
                    f"Started execution of plan via ExecutionAgent child conversation "
                    f"{child_id}"
                ),
                working_directory=working_dir,
                plan_content=plan_content[:500] + "..."
                if len(plan_content) > 500
                else plan_content,
            )

        except Exception as e:
            return ExecutePlanObservation(
                success=False, message="", error=f"Failed to execute plan: {str(e)}"
            )


ExecutePlanTool = Tool(
    name="execute_plan",
    description=EXECUTE_PLAN_DESCRIPTION,
    action_type=ExecutePlanAction,
    observation_type=ExecutePlanObservation,
    executor=ExecutePlanExecutor(),
    annotations=ToolAnnotations(
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
