"""
Agent presets for OpenHands SDK.

This package provides predefined agent configurations (tool bundles)
that can be used out of the box. Presets are intended as starting points
for common use cases, such as execution agents with shell access,
file editing, task tracking, and planning agents for research.

Usage:
    from openhands.tools.preset.default import get_execution_agent, get_planning_agent

    agent = get_execution_agent(llm)

Notes:
- Presets are simple collections of tools and configuration, not a
  replacement for custom agents.
- They are stable entry points meant to reduce boilerplate for typical
  setups.
"""

from .default import get_execution_agent, get_planning_agent


__all__ = ["get_execution_agent", "get_planning_agent"]
