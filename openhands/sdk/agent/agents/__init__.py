"""Agent implementations with auto-registration."""

from openhands.sdk.logger import get_logger


logger = get_logger(__name__)

# Import agent modules to trigger auto-registration
try:
    from openhands.sdk.agent.agents.execution import ExecutionAgentConfig  # noqa: F401
    from openhands.sdk.agent.agents.planning import PlanningAgentConfig  # noqa: F401

    logger.debug("Agent auto-registration completed")
except ImportError as e:
    logger.warning(f"Failed to import some agent configurations: {e}")
