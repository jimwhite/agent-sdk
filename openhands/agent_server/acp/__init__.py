"""Agent Client Protocol (ACP) implementation for OpenHands.

This module provides ACP support for OpenHands, enabling integration with
editors like Zed, Vim, and other ACP-compatible tools.
"""

from .server import ACPServer


__all__ = ["ACPServer"]
