from abc import ABC, abstractmethod

from openhands.sdk.conversation.secrets_manager import SecretValue
from openhands.sdk.conversation.types import ConversationID
from openhands.sdk.llm.message import Message
from openhands.sdk.security.confirmation_policy import ConfirmationPolicyBase


class BaseConversation(ABC):
    @property
    @abstractmethod
    def id(self) -> ConversationID: ...

    @abstractmethod
    def send_message(self, message: str | Message) -> None: ...

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def set_confirmation_policy(self, policy: ConfirmationPolicyBase) -> None: ...

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
