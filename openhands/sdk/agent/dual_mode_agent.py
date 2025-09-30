"""Dual-mode agent that supports both planning and execution modes."""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from openhands.sdk.agent.agent import Agent
from openhands.sdk.agent.modes import AgentMode
from openhands.sdk.event import (
    ActionEvent,
    AgentErrorEvent,
    ObservationEvent,
)
from openhands.sdk.llm import LLM
from openhands.sdk.logger import get_logger
from openhands.sdk.tool import ToolSpec
from openhands.sdk.tool.builtins.mode_switch import (
    ModeSwitchAction,
    ModeSwitchObservation,
)


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState
    from openhands.sdk.conversation.types import ConversationCallbackType

logger = get_logger(__name__)


class DualModeAgentConfig(BaseModel):
    """Configuration for dual-mode agent with separate planning and execution settings."""  # noqa: E501

    planning_llm: LLM = Field(
        ...,
        description="LLM configuration for planning mode.",
        examples=[
            {
                "model": "litellm_proxy/openai/gpt-4o",
                "base_url": "https://llm-proxy.eval.all-hands.dev",
                "api_key": "your_api_key_here",
            }
        ],
    )
    execution_llm: LLM = Field(
        ...,
        description="LLM configuration for execution mode.",
        examples=[
            {
                "model": "litellm_proxy/anthropic/claude-sonnet-4-5-20250929",
                "base_url": "https://llm-proxy.eval.all-hands.dev",
                "api_key": "your_api_key_here",
            }
        ],
    )
    planning_tools: list[ToolSpec] = Field(
        default_factory=list,
        description="Tools available in planning mode (typically read-only tools).",
    )
    execution_tools: list[ToolSpec] = Field(
        default_factory=list,
        description="Tools available in execution mode (full tool set).",
    )
    initial_mode: AgentMode = Field(
        default=AgentMode.PLANNING,
        description="Initial mode when the agent starts.",
    )


class DualModeAgent(Agent):
    """Agent that can switch between planning and execution modes.

    Planning mode is designed for read-only discussions and planning,
    while execution mode allows full tool execution capabilities.
    """

    dual_mode_config: DualModeAgentConfig = Field(
        ...,
        description="Configuration for dual-mode operation.",
    )
    current_mode: AgentMode = Field(
        default=AgentMode.PLANNING,
        description="Current operating mode of the agent.",
    )

    def __init__(self, **data):
        # Set initial mode from config
        if "current_mode" not in data and "dual_mode_config" in data:
            data["current_mode"] = data["dual_mode_config"].initial_mode

        # Set the LLM and tools based on initial mode
        config = data.get("dual_mode_config")
        if config:
            current_mode = data.get("current_mode", AgentMode.PLANNING)
            if current_mode == AgentMode.PLANNING:
                data["llm"] = config.planning_llm
                data["tools"] = config.planning_tools
                data["system_prompt_filename"] = "system_prompt_planning.j2"
            else:
                data["llm"] = config.execution_llm
                data["tools"] = config.execution_tools
                data["system_prompt_filename"] = "system_prompt_execution.j2"

        super().__init__(**data)

    def switch_mode(self, new_mode: AgentMode) -> ModeSwitchObservation:
        """Switch the agent to a different mode.

        Args:
            new_mode: The mode to switch to.

        Returns:
            ModeSwitchObservation with the result of the mode switch.
        """
        previous_mode = self.current_mode

        if new_mode == self.current_mode:
            logger.info(f"Agent is already in {new_mode} mode")
            return ModeSwitchObservation(
                previous_mode=previous_mode,
                new_mode=new_mode,
                success=True,
                message=f"Agent is already in {new_mode} mode.",
            )

        logger.info(f"Switching agent mode from {self.current_mode} to {new_mode}")

        try:
            # Update current mode
            object.__setattr__(self, "current_mode", new_mode)

            # Update LLM, tools, and system prompt based on new mode
            if new_mode == AgentMode.PLANNING:
                object.__setattr__(self, "llm", self.dual_mode_config.planning_llm)
                object.__setattr__(self, "tools", self.dual_mode_config.planning_tools)
                object.__setattr__(
                    self, "system_prompt_filename", "system_prompt_planning.j2"
                )
            else:
                object.__setattr__(self, "llm", self.dual_mode_config.execution_llm)
                object.__setattr__(self, "tools", self.dual_mode_config.execution_tools)
                object.__setattr__(
                    self, "system_prompt_filename", "system_prompt_execution.j2"
                )

            # Clear cached tools to force re-initialization
            object.__setattr__(self, "_tools", {})

            return ModeSwitchObservation(
                previous_mode=previous_mode,
                new_mode=new_mode,
                success=True,
                message=(
                    f"Successfully switched from {previous_mode} to {new_mode} mode."
                ),
            )
        except Exception as e:
            logger.error(f"Failed to switch modes: {e}")
            return ModeSwitchObservation(
                previous_mode=previous_mode,
                new_mode=previous_mode,  # Stay in previous mode on failure
                success=False,
                message=f"Failed to switch modes: {e}",
            )

    def _execute_action_event(
        self,
        state: "ConversationState",
        action_event: ActionEvent,
        on_event: "ConversationCallbackType",
    ) -> ObservationEvent:
        """Override to handle mode switch actions specially."""
        # Check if this is a mode switch action
        if action_event.tool_name == "mode_switch":
            # Handle mode switching
            mode_switch_action = action_event.action
            if isinstance(mode_switch_action, ModeSwitchAction):
                # Perform the mode switch
                observation = self.switch_mode(mode_switch_action.mode)

                # Create observation event
                obs_event = ObservationEvent(
                    observation=observation,
                    action_id=action_event.id,
                    tool_name="mode_switch",
                    tool_call_id=action_event.tool_call.id,
                )
                on_event(obs_event)
                return obs_event

        # For planning mode, restrict tool execution (except mode_switch)
        if self.current_mode == AgentMode.PLANNING and action_event.tool_name not in [
            "mode_switch",
            "finish",
            "think",
        ]:
            # In planning mode, don't execute most tools
            error_msg = (
                f"Tool '{action_event.tool_name}' is not available in planning mode. "
                "Switch to execution mode to use this tool."
            )
            error_event = AgentErrorEvent(
                error=error_msg,
                tool_name=action_event.tool_name,
                tool_call_id=action_event.tool_call.id,
            )
            on_event(error_event)
            # Return a dummy observation event to satisfy the return type
            from openhands.sdk.tool.builtins.finish import FinishObservation

            dummy_obs = FinishObservation(message=error_msg)
            return ObservationEvent(
                observation=dummy_obs,
                action_id=action_event.id,
                tool_name=action_event.tool_name,
                tool_call_id=action_event.tool_call.id,
            )

        # For all other cases, use the parent implementation
        return super()._execute_action_event(state, action_event, on_event)
