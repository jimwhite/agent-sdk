"""Built-in tool for switching agent modes."""

from collections.abc import Sequence

from pydantic import Field
from rich.text import Text

from openhands.sdk.agent.modes import AgentMode
from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool.tool import (
    ActionBase,
    ObservationBase,
    Tool,
    ToolAnnotations,
    ToolExecutor,
)


class ModeSwitchAction(ActionBase):
    """Action to switch the agent between planning and execution modes."""

    mode: AgentMode = Field(
        ...,
        description="The mode to switch to (planning or execution).",
    )
    reason: str = Field(
        default="",
        description="Optional reason for switching modes.",
    )

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation of this action."""
        content = Text()
        content.append(f"Switch to {self.mode.upper()} mode", style="bold blue")
        if self.reason:
            content.append(f"\nReason: {self.reason}")
        return content


class ModeSwitchObservation(ObservationBase):
    """Observation from switching agent modes."""

    previous_mode: AgentMode = Field(
        ...,
        description="The previous mode before switching.",
    )
    new_mode: AgentMode = Field(
        ...,
        description="The new mode after switching.",
    )
    success: bool = Field(
        ...,
        description="Whether the mode switch was successful.",
    )
    message: str = Field(
        ...,
        description="Message describing the mode switch result.",
    )

    @property
    def agent_observation(self) -> Sequence[TextContent | ImageContent]:
        return [TextContent(text=self.message)]

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation of this observation."""
        content = Text()
        if self.success:
            content.append(
                f"✓ Successfully switched from {self.previous_mode.upper()} "
                f"to {self.new_mode.upper()} mode",
                style="green",
            )
        else:
            content.append(f"✗ Failed to switch modes: {self.message}", style="red")
        return content


TOOL_DESCRIPTION = """Switch the agent between planning and execution modes.

Planning mode:
- Focus on discussion, analysis, and planning
- No tool execution capabilities
- Ideal for understanding requirements and developing strategies

Execution mode:
- Full access to tools for implementing changes
- Can execute commands, modify files, and solve technical problems
- Ideal for implementing plans and making actual changes

Use this tool when you need to switch between discussing/planning and actually
implementing solutions.
"""


class ModeSwitchExecutor(ToolExecutor):
    def __call__(self, action: ModeSwitchAction) -> ModeSwitchObservation:
        # This is a placeholder implementation
        # The actual mode switching logic will be handled by the DualModeAgent
        return ModeSwitchObservation(
            previous_mode=AgentMode.PLANNING,  # Will be updated by the agent
            new_mode=action.mode,
            success=True,
            message=f"Mode switch to {action.mode} requested. {action.reason}".strip(),
        )


ModeSwitchTool = Tool(
    name="mode_switch",
    action_type=ModeSwitchAction,
    observation_type=ModeSwitchObservation,
    description=TOOL_DESCRIPTION,
    executor=ModeSwitchExecutor(),
    annotations=ToolAnnotations(
        title="mode_switch",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
)
