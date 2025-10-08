"""OpenHands Workspace - Docker-specific workspace implementations.

This package contains Docker-specific workspace implementations and utilities:
- DockerWorkspace: Workspace backed by Docker containers
- Docker image builders with hash-based tagging
- Build utilities for custom images

For base workspace interfaces (BaseWorkspace, LocalWorkspace, RemoteWorkspace),
import from openhands.sdk.workspace.

MIGRATION NOTE:
- BaseWorkspace, LocalWorkspace, RemoteWorkspace
  -> openhands.sdk.workspace
- CommandResult, FileOperationResult -> openhands.sdk.workspace.models
- DockerWorkspace -> openhands.workspace (this package)
"""

# Docker-specific implementations
from .docker import DockerWorkspace
from .utils.exception import AgentRuntimeBuildError

__all__ = ["DockerWorkspace", "AgentRuntimeBuildError"]
