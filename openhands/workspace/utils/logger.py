"""Simple logger for the workspace package.

This module provides a basic logging setup to avoid circular dependencies
with the SDK package.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: The logger name, typically __name__ of the calling module.

    Returns:
        A configured logger instance.
    """
    return logging.getLogger(name)
