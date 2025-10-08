"""Tenacity stop condition for shutdown.

Adapted from OpenHands V0 openhands/utils/tenacity_stop.py
"""

from tenacity import RetryCallState
from tenacity.stop import stop_base

from openhands.workspace.remote_api.utils.shutdown_listener import should_exit


class stop_if_should_exit(stop_base):
    """Stop if the should_exit flag is set."""

    def __call__(self, retry_state: "RetryCallState") -> bool:
        return bool(should_exit())
