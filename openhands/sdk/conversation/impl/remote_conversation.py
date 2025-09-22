import time
import uuid

import httpx

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.base import BaseConversation
from openhands.sdk.conversation.secrets_manager import SecretValue
from openhands.sdk.conversation.state import AgentExecutionStatus
from openhands.sdk.conversation.types import ConversationCallbackType, ConversationID
from openhands.sdk.llm import Message, TextContent
from openhands.sdk.security.confirmation_policy import ConfirmationPolicyBase


class RemoteConversation(BaseConversation):
    def __init__(
        self,
        agent: AgentBase,
        host: str,
        conversation_id: ConversationID | None = None,
        callbacks: list[ConversationCallbackType] | None = None,
        max_iteration_per_run: int = 500,
        confirmation_mode: bool | None = None,
        **_: object,
    ) -> None:
        """Remote conversation proxy that talks to an agent server.

        Args:
            agent: Agent configuration (will be sent to the server)
            host: Base URL of the agent server (e.g., http://localhost:3000)
            conversation_id: Optional existing conversation id to attach to
            callbacks: Optional callbacks to receive events (not yet streamed)
            max_iteration_per_run: Max iterations configured on server
            confirmation_mode: Optional confirmation mode flag to set on start
        """
        self.agent = agent
        self._host = host.rstrip("/")
        self._client = httpx.Client(base_url=self._host, timeout=30.0)
        self._callbacks = callbacks or []
        self.max_iteration_per_run = max_iteration_per_run
        self._confirmation_mode = (
            bool(confirmation_mode) if confirmation_mode else False
        )

        if conversation_id is None:
            payload = {
                "agent": agent.model_dump(mode='json'),
                "confirmation_mode": self._confirmation_mode,
                "initial_message": None,
                "max_iterations": max_iteration_per_run,
            }
            resp = self._client.post("/conversations/", json=payload)
            resp.raise_for_status()
            data = resp.json()
            # Expect a ConversationInfo
            cid = data.get("id") or data.get("conversation_id")
            if not cid:
                raise RuntimeError(
                    "Invalid response from server: missing conversation id"
                )
            self._id = uuid.UUID(cid)
        else:
            # Attach to existing
            self._id = conversation_id
            # Validate it exists
            r = self._client.get(f"/conversations/{self._id}")
            r.raise_for_status()

    @property
    def id(self) -> ConversationID:
        return self._id

    # RemoteConversation does not expose a local ConversationState
    @property
    def state(self):  # type: ignore[override]
        raise AttributeError(
            "RemoteConversation does not expose local state; use server APIs"
        )

    def send_message(self, message: str | Message) -> None:
        if isinstance(message, str):
            message = Message(role="user", content=[TextContent(text=message)])
        assert message.role == "user", (
            "Only user messages are allowed to be sent to the agent."
        )
        payload = {
            "role": message.role,
            "content": [c.model_dump() for c in message.content],
            "run": False,  # Mirror local semantics; explicit run() must be called
        }
        resp = self._client.post(f"/conversations/{self._id}/events/", json=payload)
        resp.raise_for_status()

    def run(self) -> None:
        # Trigger a run on the server using the dedicated run endpoint
        resp = self._client.post(f"/conversations/{self._id}/run")
        resp.raise_for_status()

        # Poll for terminal states similar to local .run() behavior
        terminal = {
            AgentExecutionStatus.FINISHED.value,
            AgentExecutionStatus.WAITING_FOR_CONFIRMATION.value,
            AgentExecutionStatus.PAUSED.value,
            AgentExecutionStatus.IDLE.value,
            AgentExecutionStatus.ERROR.value,
        }
        # Simple polling loop with backoff
        for i in range(60):  # up to ~6s
            info = self._client.get(f"/conversations/{self._id}")
            info.raise_for_status()
            status = info.json().get("status")
            if status in terminal:
                break
            time.sleep(0.1)

    def set_confirmation_policy(self, policy: ConfirmationPolicyBase) -> None:
        payload = {"policy": policy.model_dump()}
        resp = self._client.post(
            f"/conversations/{self._id}/confirmation-policy", json=payload
        )
        resp.raise_for_status()

    def reject_pending_actions(self, reason: str = "User rejected the action") -> None:
        # Equivalent to rejecting confirmation: pause
        resp = self._client.post(
            f"/conversations/{self._id}/events/respond_to_confirmation",
            json={"accept": False, "reason": reason},
        )
        resp.raise_for_status()

    def pause(self) -> None:
        resp = self._client.post(f"/conversations/{self._id}/pause")
        resp.raise_for_status()

    def update_secrets(self, secrets: dict[str, SecretValue]) -> None:
        # Convert SecretValue to strings for JSON serialization
        # SecretValue can be str or callable, we need to handle both
        serializable_secrets = {}
        for key, value in secrets.items():
            if callable(value):
                # If it's a callable, call it to get the actual secret
                serializable_secrets[key] = value()
            else:
                # If it's already a string, use it directly
                serializable_secrets[key] = value

        payload = {"secrets": serializable_secrets}
        resp = self._client.post(f"/conversations/{self._id}/secrets", json=payload)
        resp.raise_for_status()

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
