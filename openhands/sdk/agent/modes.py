"""Agent modes for planning and execution."""

from enum import Enum


class AgentMode(str, Enum):
    """Enumeration of agent operating modes."""

    PLANNING = "planning"
    EXECUTION = "execution"
