"""Planning agent implementation.

Planning agents have read-only access and can:
- Read and analyze files
- Search and explore codebase structure
- Fetch external documentation
- Write detailed implementation plans

Planning agents CANNOT:
- Execute bash commands
- Modify files (except writing plans)
- Make any changes to the system
"""

from openhands.sdk.agent.agents.planning.agent import PlanningAgent


__all__ = ["PlanningAgent"]
