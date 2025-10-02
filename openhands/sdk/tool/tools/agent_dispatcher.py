"""AgentDispatcher for creating spawn child agent tools systematically."""

from typing import TYPE_CHECKING

from pydantic import Field
from rich.text import Text

from openhands.sdk.agent.registry import AgentRegistry
from openhands.sdk.conversation.registry import get_conversation_registry
from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.llm.message import TextContent
from openhands.sdk.tool import (
    Action,
    Observation,
    ToolAnnotations,
    ToolBase,
    ToolDefinition,
    ToolExecutor,
)


if TYPE_CHECKING:
    pass


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
        content.append(f"Spawning {self.agent_type.title()} Child: ", style="bold cyan")
        content.append(
            self.task_description[:100] + "..."
            if len(self.task_description) > 100
            else self.task_description,
            style="white",
        )
        return content


class SpawnChildObservation(Observation):
    """Generic observation returned after spawning a child conversation."""

    success: bool = Field(description="Whether the spawn operation was successful")
    agent_type: str = Field(description="Type of agent that was spawned")
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
                    text=f"Child {self.agent_type} spawned with ID: {self.child_conversation_id}"
                )
            ]
        else:
            return [
                TextContent(text=f"Failed to spawn {self.agent_type}: {self.error}")
            ]

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation."""
        content = Text()
        if self.success:
            content.append(f"Child {self.agent_type} spawned: ", style="bold green")
            content.append(f"{self.child_conversation_id}", style="cyan")
        else:
            content.append(f"Failed to spawn {self.agent_type}: ", style="bold red")
            content.append(f"{self.error}", style="red")
        return content


class SpawnChildExecutor(ToolExecutor):
    """Generic executor for spawning child conversations with any agent type."""

    def __init__(self, agent_type: str, conversation_id: ConversationID | None = None):
        """Initialize the executor for a specific agent type.

        Args:
            agent_type: The type of agent this executor will spawn
            conversation_id: ID of the parent conversation
        """
        self._agent_type = agent_type
        self._conversation_id = conversation_id

    def __call__(self, action: SpawnChildAction) -> SpawnChildObservation:
        """Execute the spawn child action."""
        try:
            # Check if conversation ID is provided
            if self._conversation_id is None:
                return SpawnChildObservation(
                    success=False,
                    agent_type=self._agent_type,
                    error="No conversation ID provided",
                    message="No conversation ID provided",
                )

            # Get the parent conversation
            conversation_registry = get_conversation_registry()
            parent_conversation = conversation_registry.get(self._conversation_id)

            if parent_conversation is None:
                return SpawnChildObservation(
                    success=False,
                    agent_type=self._agent_type,
                    error=f"Parent conversation {self._conversation_id} not found in registry",
                    message=f"Parent conversation {self._conversation_id} not found in registry",
                )

            # Use parent agent's LLM for child agent
            child_llm = parent_conversation.agent.llm

            # Create the child agent
            agent_registry = AgentRegistry()
            child_agent = agent_registry.create(
                agent_type=action.agent_type,
                llm=child_llm,
            )

            # Create child conversation
            child_conversation = conversation_registry.create_child_conversation(
                parent_conversation=parent_conversation,
                agent=child_agent,
                task_description=action.task_description,
            )

            return SpawnChildObservation(
                success=True,
                agent_type=self._agent_type,
                child_conversation_id=str(child_conversation._state.id),
                working_directory=parent_conversation._state.workspace.working_dir,
                message=f"{self._agent_type.title()} child created successfully",
            )

        except Exception as e:
            return SpawnChildObservation(
                success=False,
                agent_type=self._agent_type,
                error=str(e),
                message=f"Failed to create {self._agent_type} child: {str(e)}",
            )


class AgentDispatcher:
    """Factory for creating spawn child agent tools for different agent types."""

    def __init__(self):
        """Initialize the AgentDispatcher with an agent registry."""
        self._agent_registry = AgentRegistry()

    def get_available_agent_types(self) -> dict[str, str]:
        """Get available agent types and their descriptions.

        Returns:
            Dict mapping agent type names to their descriptions
        """
        return self._agent_registry.list_agents()

    def create_spawn_tool(self, agent_type: str, conversation_state) -> ToolBase:
        """Create a spawn child agent tool for the specified agent type.

        Args:
            agent_type: Type of agent to spawn
            conversation_state: The parent conversation state

        Returns:
            ToolBase: Configured tool for spawning the specified agent type

        Raises:
            ValueError: If agent_type is not available
        """
        available_types = self.get_available_agent_types()
        if agent_type not in available_types:
            raise ValueError(
                f"Agent type '{agent_type}' not found. Available types: {list(available_types.keys())}"
            )

        tool_name = f"spawn_{agent_type}_child"
        description = self._generate_tool_description(
            agent_type, available_types[agent_type]
        )

        return ToolDefinition(
            name=tool_name,
            description=description,
            action_type=SpawnChildAction,
            observation_type=SpawnChildObservation,
            executor=SpawnChildExecutor(
                agent_type=agent_type, conversation_id=conversation_state.id
            ),
            annotations=ToolAnnotations(),
        )

    def create_spawn_tool_class(self, agent_type: str):
        """Create a spawn tool class for the specified agent type.

        Args:
            agent_type: Type of agent to spawn

        Returns:
            Type: Tool class for spawning the specified agent type

        Raises:
            ValueError: If agent_type is not available
        """
        available_types = self.get_available_agent_types()
        if agent_type not in available_types:
            raise ValueError(
                f"Agent type '{agent_type}' not found. Available types: {list(available_types.keys())}"
            )

        class_name = f"Spawn{agent_type.title()}ChildTool"

        class SpawnChildTool:
            @classmethod
            def create(cls, conversation_state):
                return AgentDispatcher().create_spawn_tool(
                    agent_type, conversation_state
                )

        SpawnChildTool.__name__ = class_name
        return SpawnChildTool

    def _generate_tool_description(
        self, agent_type: str, agent_description: str
    ) -> str:
        """Generate a tool description for the specified agent type.

        Args:
            agent_type: Type of agent
            agent_description: Description of the agent's capabilities

        Returns:
            Formatted tool description
        """
        agent_name = f"{agent_type.title()}Agent"
        return (
            f"Spawn a child {agent_name} to handle specialized tasks. "
            f"{agent_description} "
            f"This operation is non-BLOCKING and leverages the agent's specialized capabilities "
            f"to work independently on the assigned task."
        )

    @staticmethod
    def create_planning_tool() -> ToolBase:
        """Create a spawn planning child tool with planning-specific configuration."""
        return AgentDispatcher().create_tool(
            agent_type="planning",
            tool_name="spawn_planning_child",
            description="Spawn a child planning agent to create detailed plans for complex tasks",
        )

    @staticmethod
    def create_tool(
        agent_type: str,
        tool_name: str | None = None,
        description: str | None = None,
    ) -> ToolBase:
        """Create a spawn child agent tool for the specified agent type.

        Args:
            agent_type: Type of agent to spawn (e.g., 'planning', 'execution', 'research')
            tool_name: Optional custom name for the tool. Defaults to 'spawn_{agent_type}_child'
            description: Optional custom description. Defaults to generic description

        Returns:
            ToolBase: Configured tool for spawning the specified agent type
        """
        if tool_name is None:
            tool_name = f"spawn_{agent_type}_child"

        if description is None:
            description = f"Spawn a child {agent_type} agent to handle a specific task"

        return ToolDefinition(
            name=tool_name,
            description=description,
            action_type=SpawnChildAction,
            observation_type=SpawnChildObservation,
            executor=SpawnChildExecutor(agent_type=agent_type),
            annotations=ToolAnnotations(),
        )
