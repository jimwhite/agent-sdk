from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from openhands.sdk.conversation.conversation_stats import ConversationStats
from openhands.sdk.conversation.secrets_manager import SecretValue
from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.llm.message import Message
from openhands.sdk.security.confirmation_policy import (
    ConfirmationPolicyBase,
    NeverConfirm,
)
from openhands.sdk.utils.protocol import ListLike


if TYPE_CHECKING:
    from openhands.sdk.conversation.state import AgentExecutionStatus
    from openhands.sdk.event.base import EventBase


class ConversationStateProtocol(Protocol):
    """Protocol defining the interface for conversation state objects."""

    @property
    def id(self) -> ConversationID:
        """The conversation ID."""
        ...

    @property
    def events(self) -> ListLike["EventBase"]:
        """Access to the events list."""
        ...

    @property
    def agent_status(self) -> "AgentExecutionStatus":
        """The current agent execution status."""
        ...

    @property
    def confirmation_policy(self) -> ConfirmationPolicyBase:
        """The confirmation policy."""
        ...

    @property
    def activated_knowledge_microagents(self) -> list[str]:
        """List of activated knowledge microagents."""
        ...


class BaseConversation(ABC):
    @property
    @abstractmethod
    def id(self) -> ConversationID: ...

    @property
    @abstractmethod
    def state(self) -> ConversationStateProtocol: ...

    @property
    @abstractmethod
    def conversation_stats(self) -> ConversationStats: ...

    @abstractmethod
    def send_message(self, message: str | Message) -> None: ...

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def set_confirmation_policy(self, policy: ConfirmationPolicyBase) -> None: ...

    @property
    def confirmation_policy_active(self) -> bool:
        return not isinstance(self.state.confirmation_policy, NeverConfirm)

    @abstractmethod
    def reject_pending_actions(
        self, reason: str = "User rejected the action"
    ) -> None: ...

    @abstractmethod
    def pause(self) -> None: ...

    @abstractmethod
    def update_secrets(self, secrets: dict[str, SecretValue]) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    # System-level operations
    @abstractmethod
    async def execute_bash(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Execute a bash command on the system.

        These system operations are independent of the conversation itself.
        A system can spawn multiple conversations, and these functionalities
        can be accessed without connecting to a system. The reason these
        methods are tied to conversation is mostly for convenience, and maybe
        later they will be scoped based on the workspace of the conversation.

        Args:
            command: The bash command to execute
            cwd: Working directory for the command (optional)
            timeout: Timeout in seconds (defaults to 30.0)

        Returns:
            dict: Result containing stdout, stderr, exit_code, and other metadata

        Raises:
            Exception: If command execution fails
        """
        ...

    @abstractmethod
    async def file_upload(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Upload a file to the system.

        These system operations are independent of the conversation itself.
        A system can spawn multiple conversations, and these functionalities
        can be accessed without connecting to a system. The reason these
        methods are tied to conversation is mostly for convenience, and maybe
        later they will be scoped based on the workspace of the conversation.

        Args:
            source_path: Path to the source file
            destination_path: Path where the file should be uploaded

        Returns:
            dict: Result containing success status and metadata

        Raises:
            Exception: If file upload fails
        """
        ...

    @abstractmethod
    async def file_download(
        self,
        source_path: str | Path,
        destination_path: str | Path,
    ) -> dict[str, Any]:
        """Download a file from the system.

        These system operations are independent of the conversation itself.
        A system can spawn multiple conversations, and these functionalities
        can be accessed without connecting to a system. The reason these
        methods are tied to conversation is mostly for convenience, and maybe
        later they will be scoped based on the workspace of the conversation.

        Args:
            source_path: Path to the source file on the system
            destination_path: Path where the file should be downloaded

        Returns:
            dict: Result containing success status and metadata

        Raises:
            Exception: If file download fails
        """
        ...
