"""Agent implementations organized by type.

This package contains specialized agent implementations:
- execution: Full read-write agents for implementation tasks
- planning: Read-only agents for research and planning

Agents are automatically registered with the AgentRegistry on import,
allowing for dynamic instantiation via AgentRegistry.create().
"""

from openhands.sdk.agent.agents.execution import ExecutionAgent
from openhands.sdk.agent.agents.execution.config import ExecutionAgentConfig
from openhands.sdk.agent.agents.planning import PlanningAgent
from openhands.sdk.agent.agents.planning.config import PlanningAgentConfig
from openhands.sdk.agent.registry import AgentRegistry


# Auto-register agents on import
def _register_agents():
    """Register all built-in agents with the registry."""
    try:
        AgentRegistry.register("execution", ExecutionAgentConfig())
    except ValueError:
        pass  # Already registered

    try:
        AgentRegistry.register("planning", PlanningAgentConfig())
    except ValueError:
        pass  # Already registered


_register_agents()


__all__ = [
    "ExecutionAgent",
    "PlanningAgent",
]
