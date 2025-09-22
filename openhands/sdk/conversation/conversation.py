from typing import Iterable

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.impl import LocalConversation, RemoteConversation
from openhands.sdk.conversation.types import ConversationCallbackType, ConversationID
from openhands.sdk.io import FileStore
from openhands.sdk.logger import get_logger


logger = get_logger(__name__)


def compose_callbacks(
    callbacks: Iterable[ConversationCallbackType],
) -> ConversationCallbackType:
    def composed(event) -> None:
        for cb in callbacks:
            if cb:
                cb(event)

    return composed


class Conversation:
    """Factory entrypoint that returns a LocalConversation or RemoteConversation.

    Usage:
        - Conversation(agent=...) -> LocalConversation
        - Conversation(agent=..., host="http://...") -> RemoteConversation
    """

    def __new__(
        cls,
        agent: AgentBase,
        persist_filestore: FileStore | None = None,
        conversation_id: ConversationID | None = None,
        callbacks: list[ConversationCallbackType] | None = None,
        max_iteration_per_run: int = 500,
        visualize: bool = True,
        host: str | None = None,
        confirmation_mode: bool | None = None,
    ):
        if cls is Conversation:
            if host:
                return RemoteConversation(
                    agent=agent,
                    host=host,
                    conversation_id=conversation_id,
                    callbacks=callbacks,
                    max_iteration_per_run=max_iteration_per_run,
                    confirmation_mode=confirmation_mode,
                )
            return LocalConversation(
                agent=agent,
                persist_filestore=persist_filestore,
                conversation_id=conversation_id,
                callbacks=callbacks,
                max_iteration_per_run=max_iteration_per_run,
                visualize=visualize,
            )
        return super().__new__(cls)
