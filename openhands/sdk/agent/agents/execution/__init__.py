"""Execution agent implementation.

Execution agents have full read-write access and can:
- Execute bash commands
- Modify files
- Create and manage tasks
- Browse the web (optional)
"""

from openhands.sdk.agent.agents.execution.agent import ExecutionAgent


__all__ = ["ExecutionAgent"]
