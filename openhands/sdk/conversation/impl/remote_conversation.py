import asyncio
import json
import threading
import time
import uuid
from typing import SupportsIndex, overload
from urllib.parse import urlparse

import httpx
import websockets

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.base import BaseConversation, ConversationStateProtocol
from openhands.sdk.conversation.secrets_manager import SecretValue
from openhands.sdk.conversation.state import AgentExecutionStatus
from openhands.sdk.conversation.types import ConversationCallbackType, ConversationID
from openhands.sdk.event.base import EventBase
from openhands.sdk.llm import Message, TextContent
from openhands.sdk.logger import get_logger
from openhands.sdk.security.confirmation_policy import (
    ConfirmationPolicyBase,
    NeverConfirm,
)
from openhands.sdk.utils.protocol import ListLike


logger = get_logger(__name__)


class WebSocketCallbackClient:
    """WebSocket client that connects to agent server and forwards events."""

    def __init__(
        self,
        host: str,
        conversation_id: str,
        callbacks: list[ConversationCallbackType],
    ):
        self.host = host
        self.conversation_id = conversation_id
        self.callbacks = callbacks
        self._websocket = None
        self._task = None
        self._loop = None
        self._thread = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start the WebSocket client in a background thread."""
        if self._thread is not None:
            return  # Already started

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_in_thread, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the WebSocket client."""
        if self._thread is None:
            return  # Not started

        self._stop_event.set()

        # Cancel the task if it exists
        if self._task and self._loop:
            self._loop.call_soon_threadsafe(self._task.cancel)

        # Wait for thread to finish
        self._thread.join(timeout=5.0)
        self._thread = None

    def _run_in_thread(self) -> None:
        """Run the WebSocket client in a separate thread with its own event loop."""
        try:
            # Create a new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            # Run the WebSocket client
            self._task = self._loop.create_task(self._websocket_client())
            self._loop.run_until_complete(self._task)
        except asyncio.CancelledError:
            logger.debug("WebSocket client task was cancelled")
        except Exception as e:
            logger.error(f"WebSocket client error: {e}", exc_info=True)
        finally:
            if self._loop:
                self._loop.close()

    async def _websocket_client(self) -> None:
        """Main WebSocket client coroutine."""
        # Convert HTTP URL to WebSocket URL
        parsed = urlparse(self.host)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_url = f"{ws_scheme}://{parsed.netloc}/api/conversations/{self.conversation_id}/events/socket"

        logger.debug(f"Connecting to WebSocket: {ws_url}")

        max_retries = 5
        retry_delay = 1.0

        for attempt in range(max_retries):
            if self._stop_event.is_set():
                break

            try:
                async with websockets.connect(ws_url) as websocket:
                    self._websocket = websocket
                    logger.debug("WebSocket connected successfully")

                    # Listen for events
                    async for message in websocket:
                        if self._stop_event.is_set():
                            break

                        try:
                            # Parse the event
                            event_data = json.loads(message)
                            event = EventBase.model_validate(event_data)

                            # Forward to all callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(event)
                                except Exception as e:
                                    logger.error(
                                        f"Error in callback: {e}", exc_info=True
                                    )

                        except Exception as e:
                            logger.error(
                                f"Error processing WebSocket message: {e}",
                                exc_info=True,
                            )

            except websockets.exceptions.ConnectionClosed:
                logger.debug("WebSocket connection closed")
                break
            except Exception as e:
                logger.warning(
                    f"WebSocket connection attempt {attempt + 1} failed: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(
                        retry_delay * 2, 30.0
                    )  # Exponential backoff, max 30s
                else:
                    logger.error("Max WebSocket connection retries exceeded")
                    break
            finally:
                self._websocket = None


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
                f"/api/conversations/{self._conversation_id}/events/search",
                params=params,
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


class RemoteState(ConversationStateProtocol):
    """A state-like interface for accessing remote conversation state."""

    def __init__(self, client: httpx.Client, conversation_id: str):
        self._client = client
        self._conversation_id = conversation_id
        self._events = RemoteEventsList(client, conversation_id)

    def _get_conversation_info(self) -> dict:
        """Fetch the latest conversation info from the remote API."""
        resp = self._client.get(f"/api/conversations/{self._conversation_id}")
        resp.raise_for_status()
        return resp.json()

    @property
    def events(self) -> RemoteEventsList:
        """Access to the events list."""
        return self._events

    @property
    def id(self) -> ConversationID:
        """The conversation ID."""
        return uuid.UUID(self._conversation_id)

    @property
    def agent_status(self) -> AgentExecutionStatus:
        """The current agent execution status."""
        info = self._get_conversation_info()
        status_str = info.get("agent_status", "idle")
        return AgentExecutionStatus(status_str)

    @property
    def confirmation_policy(self) -> ConfirmationPolicyBase:
        """The confirmation policy."""
        info = self._get_conversation_info()
        policy_data = info.get("confirmation_policy")
        if policy_data is None:
            return NeverConfirm()

        # Deserialize the confirmation policy from the API response
        # The policy_data should be a dict with the policy configuration
        try:
            return ConfirmationPolicyBase.model_validate(policy_data)
        except Exception as e:
            logger.warning(f"Failed to deserialize confirmation policy: {e}")
            return NeverConfirm()

    @property
    def activated_knowledge_microagents(self) -> list[str]:
        """List of activated knowledge microagents."""
        info = self._get_conversation_info()
        return info.get("activated_knowledge_microagents", [])


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
                "agent": agent.model_dump(
                    mode="json", context={"expose_secrets": True}
                ),
                "confirmation_mode": self._confirmation_mode,
                "initial_message": None,
                "max_iterations": max_iteration_per_run,
            }
            resp = self._client.post("/api/conversations/", json=payload)
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
            r = self._client.get(f"/api/conversations/{self._id}")
            r.raise_for_status()

        # Initialize the remote state
        self._state = RemoteState(self._client, str(self._id))

        # Initialize WebSocket client for callbacks if provided
        self._ws_client = None
        if self._callbacks:
            self._ws_client = WebSocketCallbackClient(
                host=self._host,
                conversation_id=str(self._id),
                callbacks=self._callbacks,
            )
            self._ws_client.start()

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
        resp = self._client.post(f"/api/conversations/{self._id}/events/", json=payload)
        resp.raise_for_status()

    def run(self) -> None:
        current_status = self.state.agent_status
        if current_status != AgentExecutionStatus.RUNNING:
            # Trigger a run on the server using the dedicated run endpoint
            resp = self._client.post(f"/api/conversations/{self._id}/run")
            resp.raise_for_status()
        else:
            logger.debug("Conversation is already running; skipping run trigger")

        # 120 * 0.5 = 60s timeout per iteration
        max_iterations = self.max_iteration_per_run * 120
        for i in range(max_iterations):
            current_status = self.state.agent_status
            if current_status != AgentExecutionStatus.RUNNING:
                # Add a small delay to ensure background task cleanup is complete
                time.sleep(0.5)
                break
            time.sleep(0.5)
        else:
            # If we exit the loop without breaking, we timed out
            raise TimeoutError(
                f"Agent did not reach terminal state within {max_iterations * 0.5}s. "
                f"Current status: {self.state.agent_status}"
            )

    def set_confirmation_policy(self, policy: ConfirmationPolicyBase) -> None:
        payload = {"policy": policy.model_dump()}
        resp = self._client.post(
            f"/api/conversations/{self._id}/confirmation-policy", json=payload
        )
        resp.raise_for_status()

    def reject_pending_actions(self, reason: str = "User rejected the action") -> None:
        # Equivalent to rejecting confirmation: pause
        resp = self._client.post(
            f"/api/conversations/{self._id}/events/respond_to_confirmation",
            json={"accept": False, "reason": reason},
        )
        resp.raise_for_status()

    def pause(self) -> None:
        resp = self._client.post(f"/api/conversations/{self._id}/pause")
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
        resp = self._client.post(f"/api/conversations/{self._id}/secrets", json=payload)
        resp.raise_for_status()

    def close(self) -> None:
        try:
            # Stop WebSocket client if it exists
            if self._ws_client:
                self._ws_client.stop()
                self._ws_client = None
        except Exception:
            pass

        try:
            self._client.close()
        except Exception:
            pass

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
