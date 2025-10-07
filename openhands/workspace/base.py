from abc import ABC

from openhands.sdk.logger import get_logger
from openhands.sdk.workspace import Workspace


logger = get_logger(__name__)


class BaseWorkspace(Workspace, ABC):
    """Abstract base mixin for workspace.

    All workspace implementations support the context manager protocol,
    allowing safe resource management:

        with workspace:
            workspace.execute_command("echo 'hello'")
    """

    # Concrete implementations of abstract methods will be provided by subclasses
