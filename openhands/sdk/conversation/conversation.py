from typing import TYPE_CHECKING, Self

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.base import BaseConversation
from openhands.sdk.conversation.secrets_manager import SecretValue
from openhands.sdk.conversation.types import ConversationCallbackType, ConversationID
from openhands.sdk.logger import get_logger
from openhands.sdk.workspace import Workspace


if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class Conversation:
    """Factory entrypoint that returns a LocalConversation or RemoteConversation.

    Usage:
        - Conversation(agent=...) -> LocalConversation
        - Conversation(agent=..., host="http://...") -> RemoteConversation
    """

    def __new__(
        cls: type[Self],
        agent: AgentBase,
        *,
        workspace: Workspace,
        persistence_dir: str | None = None,
        conversation_id: ConversationID | None = None,
        callbacks: list[ConversationCallbackType] | None = None,
        max_iteration_per_run: int = 500,
        stuck_detection: bool = True,
        visualize: bool = True,
        secrets: dict[str, SecretValue] | dict[str, str] | None = None,
    ) -> BaseConversation:
        from openhands.sdk.conversation.impl.local_conversation import LocalConversation
        from openhands.sdk.conversation.impl.remote_conversation import (
            RemoteConversation,
        )

        if workspace.get_workspace_type() in ("remote", "docker"):
            # For RemoteConversation, persistence_dir should not be used
            # Only check if it was explicitly set to something other than the default
            if persistence_dir is not None:
                raise ValueError(
                    "persistence_dir should not be set when using RemoteConversation"
                )
            return RemoteConversation(
                agent=agent,
                conversation_id=conversation_id,
                callbacks=callbacks,
                max_iteration_per_run=max_iteration_per_run,
                stuck_detection=stuck_detection,
                visualize=visualize,
                workspace=workspace,
                secrets=secrets,
            )

        return LocalConversation(
            agent=agent,
            conversation_id=conversation_id,
            callbacks=callbacks,
            max_iteration_per_run=max_iteration_per_run,
            stuck_detection=stuck_detection,
            visualize=visualize,
            workspace=workspace,
            persistence_dir=persistence_dir,
            secrets=secrets,
        )
