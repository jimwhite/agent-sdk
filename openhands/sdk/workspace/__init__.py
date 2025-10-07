"""Workspace abstractions and implementations for OpenHands SDK.

This package provides the base workspace interfaces and implementations:
- BaseWorkspace: Abstract base class for all workspace types
- LocalWorkspace: Direct local file system and process execution
- RemoteWorkspace: Remote execution via HTTP API
- APIRemoteWorkspace: Remote execution with API sandbox features
"""

from openhands.sdk.workspace.base import BaseWorkspace
from openhands.sdk.workspace.local import LocalWorkspace
from openhands.sdk.workspace.models import CommandResult, FileOperationResult
from openhands.sdk.workspace.remote import APIRemoteWorkspace, RemoteWorkspace


__all__ = [
    "APIRemoteWorkspace",
    "BaseWorkspace",
    "CommandResult",
    "FileOperationResult",
    "LocalWorkspace",
    "RemoteWorkspace",
]
