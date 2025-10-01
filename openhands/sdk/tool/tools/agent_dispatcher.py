"""AgentDispatcher for creating spawn child agent tools systematically."""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk.agent.registry import AgentRegistry
from openhands.sdk.conversation.registry import get_conversation_registry
from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.llm.message import ImageContent, TextContent
from openhands.sdk.tool import (
    Action,
    Observation,
    ToolAnnotations,
    ToolBase,
    ToolDefinition,
    ToolExecutor,
)


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import ConversationState


class SpawnChildAction(Action):
    """Generic action for spawning a child conversation with any agent type."""

    task_description: str = Field(
        description="Description of the task for the child agent"
    )
    agent_type: str = Field(description="Type of agent to spawn")

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation."""
        content = Text()

        # Agent-specific emojis and styling
        agent_emojis = {
            "planning": ("🧠", "blue"),
            "execution": ("⚡", "yellow"),
            "analysis": ("🔍", "cyan"),
            "research": ("📚", "magenta"),
        }

        emoji, style = agent_emojis.get(self.agent_type, ("🤖", "white"))

        content.append(f"{emoji} ", style=style)
        content.append(
            f"Spawning {self.agent_type.title()} Child: ", style=f"bold {style}"
        )
        content.append(
            self.task_description[:100] + "..."
            if len(self.task_description) > 100
            else self.task_description,
            style="white",
        )
        return content


class SpawnChildObservation(Observation):
    """Generic observation returned after spawning a child conversation."""

    success: bool = Field(description="Whether the operation was successful")
    child_conversation_id: str | None = Field(
        default=None, description="ID of the created child conversation"
    )
    message: str = Field(description="Status message")
    working_directory: str | None = Field(
        default=None, description="Working directory of the child conversation"
    )
    agent_type: str = Field(description="Type of agent that was spawned")
    error: str | None = Field(default=None, description="Error message if failed")

    @property
    def to_llm_content(self) -> Sequence[TextContent | ImageContent]:
        if self.success:
            text_parts = [
                f"✅ {self.message}",
                f"Child ID: {self.child_conversation_id}",
                f"Agent Type: {self.agent_type}",
                f"Working Directory: {self.working_directory}",
            ]
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


class SpawnChildExecutor(ToolExecutor):
    """Generic executor for spawning child conversations with any agent type."""

    def __init__(self, agent_type: str, conversation_id: ConversationID | None = None):
        """Initialize the executor with agent type and conversation ID."""
        self._agent_type = agent_type
        self._conversation_id = conversation_id

    def __call__(self, action: SpawnChildAction) -> SpawnChildObservation:
        # Get the current conversation from the global registry
        if not self._conversation_id:
            return SpawnChildObservation(
                success=False,
                message="",
                agent_type=self._agent_type,
                error=(
                    "No conversation ID provided. This tool can only be used within a "
                    "conversation context."
                ),
            )

        registry = get_conversation_registry()
        conversation = registry.get(self._conversation_id)
        if not conversation:
            return SpawnChildObservation(
                success=False,
                message="",
                agent_type=self._agent_type,
                error=(f"Conversation {self._conversation_id} not found in registry."),
            )

        try:
            # Get working directory from parent conversation before creating child
            state = getattr(conversation, "_state", None)
            if not state:
                raise ValueError("Conversation state not available")
            working_dir = state.workspace.working_dir

            agent_registry = AgentRegistry()
            parent_agent = getattr(conversation, "agent", None)
            if not parent_agent:
                raise ValueError("Parent conversation agent not available")

            child_agent = agent_registry.create(
                self._agent_type,
                llm=parent_agent.llm,
                system_prompt_kwargs={"WORK_DIR": working_dir},
            )

            # Create child conversation directly through registry
            conv_registry = get_conversation_registry()
            child_conversation = conv_registry.create_child_conversation(
                parent_id=state.id,
                agent=child_agent,
                visualize=True,
            )

            child_state = getattr(child_conversation, "_state", None)
            if not child_state:
                raise ValueError("Child conversation state not available")

            return SpawnChildObservation(
                success=True,
                child_conversation_id=str(child_state.id),
                message=f"{self._agent_type.title()} child created.",
                working_directory=working_dir,
                agent_type=self._agent_type,
            )

        except Exception as e:
            return SpawnChildObservation(
                success=False,
                message="",
                agent_type=self._agent_type,
                error=f"Failed to spawn {self._agent_type} child: {str(e)}",
            )


class AgentDispatcher:
    """Dispatcher for creating spawn child agent tools systematically."""

    def __init__(self):
        """Initialize the AgentDispatcher."""
        self._agent_registry = AgentRegistry()

    def create_spawn_tool(
        self, agent_type: str, conv_state: "ConversationState"
    ) -> ToolBase[SpawnChildAction, SpawnChildObservation]:
        """Create a spawn tool for the specified agent type.

        Args:
            agent_type: The type of agent to create a spawn tool for
            conv_state: The conversation state containing the conversation ID

        Returns:
            A Tool instance for spawning the specified agent type

        Raises:
            ValueError: If the agent type is not registered
        """
        # Get agent metadata from registry
        available_agents = self._agent_registry.list_agents()
        if agent_type not in available_agents:
            raise ValueError(
                f"Agent type '{agent_type}' not found. "
                f"Available types: {list(available_agents.keys())}"
            )

        agent_description = available_agents[agent_type]

        # Create tool metadata based on agent type
        tool_name = f"spawn_{agent_type}_child"
        tool_description = self._generate_tool_description(
            agent_type, agent_description
        )

        # Create executor
        executor = SpawnChildExecutor(
            agent_type=agent_type, conversation_id=conv_state.id
        )

        # Create and return the tool
        return ToolDefinition(
            name=tool_name,
            description=tool_description,
            action_type=SpawnChildAction,
            observation_type=SpawnChildObservation,
            executor=executor,
            annotations=ToolAnnotations(
                readOnlyHint=False,
                destructiveHint=False,
                idempotentHint=False,
                openWorldHint=True,
            ),
        )

    def create_spawn_tool_class(self, agent_type: str) -> type[ToolBase]:
        """Create a ToolBase subclass for the specified agent type.

        Args:
            agent_type: The type of agent to create a tool class for

        Returns:
            A ToolBase subclass for spawning the specified agent type

        Raises:
            ValueError: If the agent type is not registered
        """
        # Get agent metadata from registry
        available_agents = self._agent_registry.list_agents()
        if agent_type not in available_agents:
            raise ValueError(
                f"Agent type '{agent_type}' not found. "
                f"Available types: {list(available_agents.keys())}"
            )

        agent_description = available_agents[agent_type]
        tool_description = self._generate_tool_description(
            agent_type, agent_description
        )

        class DynamicSpawnTool(ToolBase):
            """Dynamically created tool for spawning child conversations."""

            @classmethod
            def create(
                cls, conv_state: "ConversationState", **params
            ) -> list[ToolBase[SpawnChildAction, SpawnChildObservation]]:
                """Create a spawn tool instance.

                Args:
                    conv_state: The conversation state containing the conversation ID
                    **params: Additional parameters (not used)

                Returns:
                    A list containing a single Tool instance.
                """
                executor = SpawnChildExecutor(
                    agent_type=agent_type, conversation_id=conv_state.id
                )

                tool = ToolDefinition(
                    name=f"spawn_{agent_type}_child",
                    description=tool_description,
                    action_type=SpawnChildAction,
                    observation_type=SpawnChildObservation,
                    executor=executor,
                    annotations=ToolAnnotations(
                        readOnlyHint=False,
                        destructiveHint=False,
                        idempotentHint=False,
                        openWorldHint=True,
                    ),
                )
                return [tool]

        # Set a meaningful class name
        DynamicSpawnTool.__name__ = f"Spawn{agent_type.title()}ChildTool"
        DynamicSpawnTool.__qualname__ = f"Spawn{agent_type.title()}ChildTool"

        return DynamicSpawnTool

    def _generate_tool_description(
        self, agent_type: str, agent_description: str
    ) -> str:
        """Generate a tool description based on agent type and description.

        Args:
            agent_type: The type of agent
            agent_description: The description of the agent's capabilities

        Returns:
            A formatted tool description
        """
        return (
            f"Spawn a child conversation with a {agent_type.title()}Agent. "
            f"This tool is non-BLOCKING. "
            f"Use this when you need to delegate work to a specialized agent.\n\n"
            f"Agent capabilities: {agent_description}\n\n"
            f"The tool will:\n"
            f"1. Create a {agent_type.title()}Agent child conversation\n"
            f"2. Return an observation with the child conversation details.\n"
            f"The {agent_type} agent will handle the delegated task according to its "
            f"specialized capabilities."
        )

    def get_available_agent_types(self) -> dict[str, str]:
        """Get all available agent types and their descriptions.

        Returns:
            Dictionary mapping agent type names to their descriptions
        """
        return self._agent_registry.list_agents()
