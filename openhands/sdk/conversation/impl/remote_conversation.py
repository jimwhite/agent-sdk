import time
import uuid
from typing import SupportsIndex, overload

import httpx

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.base import BaseConversation
from openhands.sdk.conversation.secrets_manager import SecretValue
from openhands.sdk.conversation.state import AgentExecutionStatus
from openhands.sdk.conversation.types import ConversationCallbackType, ConversationID
from openhands.sdk.event.base import EventBase
from openhands.sdk.llm import Message, TextContent
from openhands.sdk.security.confirmation_policy import ConfirmationPolicyBase
from openhands.sdk.utils.protocol import ListLike


class RemoteEventsList(ListLike[EventBase]):
    """A list-like interface for accessing events from a remote conversation."""

    def __init__(self, client: httpx.Client, conversation_id: str):
        self._client = client
        self._conversation_id = conversation_id
        self._cached_events: list[EventBase] | None = None

    def _fetch_all_events(self) -> list[EventBase]:
        """Fetch all events from the remote API."""
        if self._cached_events is not None:
            return self._cached_events

        events = []
        page_id = None

        while True:
            params = {"limit": 100}
            if page_id:
                params["page_id"] = page_id

            resp = self._client.get(
                f"/conversations/{self._conversation_id}/events/search", params=params
            )
            resp.raise_for_status()
            data = resp.json()

            events.extend(data["items"])

            if not data.get("next_page_id"):
                break
            page_id = data["next_page_id"]

        self._cached_events = events
        return events

    def __len__(self) -> int:
        return len(self._fetch_all_events())

    @overload
    def __getitem__(self, index: SupportsIndex, /) -> EventBase: ...

    @overload
    def __getitem__(self, index: slice, /) -> list[EventBase]: ...

    def __getitem__(
        self,
        index: SupportsIndex | slice,
        /,
    ) -> EventBase | list[EventBase]:
        events = self._fetch_all_events()
        return events[index]

    def __iter__(self):
        return iter(self._fetch_all_events())

    def append(self, event: EventBase) -> None:
        # For remote conversations, events are added via API calls
        # This method is here for interface compatibility but shouldn't be used directly
        raise NotImplementedError(
            "Cannot directly append events to remote conversation"
        )

    def clear_cache(self) -> None:
        """Clear the cached events to force a fresh fetch on next access."""
        self._cached_events = None


class RemoteState:
    """A state-like interface for accessing remote conversation state."""

    def __init__(self, client: httpx.Client, conversation_id: str):
        self._client = client
        self._conversation_id = conversation_id
        self._events = RemoteEventsList(client, conversation_id)

    @property
    def events(self) -> RemoteEventsList:
        """Access to the events list."""
        return self._events

    @property
    def id(self) -> ConversationID:
        """The conversation ID."""
        return uuid.UUID(self._conversation_id)


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
                "agent": agent.model_dump(mode="json"),
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

        # Initialize the remote state
        self._state = RemoteState(self._client, str(self._id))

    @property
    def id(self) -> ConversationID:
        return self._id

    @property
    def state(self) -> RemoteState:
        """Access to remote conversation state."""
        return self._state

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
