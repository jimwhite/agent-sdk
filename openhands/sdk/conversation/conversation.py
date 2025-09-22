import time
import uuid
from typing import Iterable

import httpx

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation.secrets_manager import SecretValue
from openhands.sdk.conversation.state import AgentExecutionStatus, ConversationState
from openhands.sdk.conversation.types import ConversationCallbackType, ConversationID
from openhands.sdk.conversation.visualizer import (
    create_default_visualizer,
)
from openhands.sdk.event import (
    MessageEvent,
    PauseEvent,
    UserRejectObservation,
)
from openhands.sdk.event.utils import get_unmatched_actions
from openhands.sdk.io import FileStore
from openhands.sdk.llm import Message, TextContent
from openhands.sdk.logger import get_logger
from openhands.sdk.security.confirmation_policy import ConfirmationPolicyBase


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


class LocalConversation(Conversation):
    def __init__(
        self,
        agent: AgentBase,
        persist_filestore: FileStore | None = None,
        conversation_id: ConversationID | None = None,
        callbacks: list[ConversationCallbackType] | None = None,
        max_iteration_per_run: int = 500,
        visualize: bool = True,
        **_: object,
    ):
        """Initialize the conversation.

        Args:
            agent: The agent to use for the conversation
            persist_filestore: Optional FileStore to persist conversation state
            conversation_id: Optional ID for the conversation. If provided, will
                      be used to identify the conversation. The user might want to
                      suffix their persistent filestore with this ID.
            callbacks: Optional list of callback functions to handle events
            max_iteration_per_run: Maximum number of iterations per run
            visualize: Whether to enable default visualization. If True, adds
                      a default visualizer callback. If False, relies on
                      application to provide visualization through callbacks.
        """
        self.agent = agent
        self._persist_filestore = persist_filestore

        # Create-or-resume: factory inspects BASE_STATE to decide
        desired_id = conversation_id or uuid.uuid4()
        self.state = ConversationState.create(
            id=desired_id,
            agent=agent,
            file_store=self._persist_filestore,
        )

        # Default callback: persist every event to state
        def _default_callback(e):
            self.state.events.append(e)

        composed_list = (callbacks if callbacks else []) + [_default_callback]
        # Add default visualizer if requested
        if visualize:
            self._visualizer = create_default_visualizer()
            composed_list = [self._visualizer.on_event] + composed_list
            # visualize should happen first for visibility
        else:
            self._visualizer = None

        self._on_event = compose_callbacks(composed_list)
        self.max_iteration_per_run = max_iteration_per_run

        with self.state:
            self.agent.init_state(self.state, on_event=self._on_event)

    @property
    def id(self) -> ConversationID:
        """Get the unique ID of the conversation."""
        return self.state.id

    def send_message(self, message: str | Message) -> None:
        """Send a message to the agent.

        Args:
            message: Either a string (which will be converted to a user message)
                    or a Message object
        """
        # Convert string to Message if needed
        if isinstance(message, str):
            message = Message(role="user", content=[TextContent(text=message)])

        assert message.role == "user", (
            "Only user messages are allowed to be sent to the agent."
        )
        with self.state:
            if self.state.agent_status == AgentExecutionStatus.FINISHED:
                self.state.agent_status = (
                    AgentExecutionStatus.IDLE
                )  # now we have a new message

            # TODO: We should add test cases for all these scenarios
            activated_microagent_names: list[str] = []
            extended_content: list[TextContent] = []

            # Handle per-turn user message (i.e., knowledge agent trigger)
            if self.agent.agent_context:
                ctx = self.agent.agent_context.get_user_message_suffix(
                    user_message=message,
                    # We skip microagents that were already activated
                    skip_microagent_names=self.state.activated_knowledge_microagents,
                )
                # TODO(calvin): we need to update
                # self.state.activated_knowledge_microagents
                # so condenser can work
                if ctx:
                    content, activated_microagent_names = ctx
                    logger.debug(
                        f"Got augmented user message content: {content}, "
                        f"activated microagents: {activated_microagent_names}"
                    )
                    extended_content.append(content)
                    self.state.activated_knowledge_microagents.extend(
                        activated_microagent_names
                    )

            user_msg_event = MessageEvent(
                source="user",
                llm_message=message,
                activated_microagents=activated_microagent_names,
                extended_content=extended_content,
            )
            self._on_event(user_msg_event)

    def run(self) -> None:
        """Runs the conversation until the agent finishes.

        In confirmation mode:
        - First call: creates actions but doesn't execute them, stops and waits
        - Second call: executes pending actions (implicit confirmation)

        In normal mode:
        - Creates and executes actions immediately

        Can be paused between steps
        """

        with self.state:
            if self.state.agent_status == AgentExecutionStatus.PAUSED:
                self.state.agent_status = AgentExecutionStatus.RUNNING

        iteration = 0
        while True:
            logger.debug(f"Conversation run iteration {iteration}")
            with self.state:
                # Pause attempts to acquire the state lock
                # Before value can be modified step can be taken
                # Ensure step conditions are checked when lock is already acquired
                if self.state.agent_status in [
                    AgentExecutionStatus.FINISHED,
                    AgentExecutionStatus.PAUSED,
                ]:
                    break

                # clear the flag before calling agent.step() (user approved)
                if (
                    self.state.agent_status
                    == AgentExecutionStatus.WAITING_FOR_CONFIRMATION
                ):
                    self.state.agent_status = AgentExecutionStatus.RUNNING

                # step must mutate the SAME state object
                self.agent.step(self.state, on_event=self._on_event)

            # In confirmation mode, stop after one iteration if waiting for confirmation
            if self.state.agent_status == AgentExecutionStatus.WAITING_FOR_CONFIRMATION:
                break

            iteration += 1
            if iteration >= self.max_iteration_per_run:
                break

    def set_confirmation_policy(self, policy: ConfirmationPolicyBase) -> None:
        """Set the confirmation policy and store it in conversation state."""
        with self.state:
            self.state.confirmation_policy = policy
        logger.info(f"Confirmation policy set to: {policy}")

    def reject_pending_actions(self, reason: str = "User rejected the action") -> None:
        """Reject all pending actions from the agent.

        This is a non-invasive method to reject actions between run() calls.
        Also clears the agent_waiting_for_confirmation flag.
        """
        pending_actions = get_unmatched_actions(self.state.events)

        with self.state:
            # Always clear the agent_waiting_for_confirmation flag
            if self.state.agent_status == AgentExecutionStatus.WAITING_FOR_CONFIRMATION:
                self.state.agent_status = AgentExecutionStatus.IDLE

            if not pending_actions:
                logger.warning("No pending actions to reject")
                return

            for action_event in pending_actions:
                # Create rejection observation
                rejection_event = UserRejectObservation(
                    action_id=action_event.id,
                    tool_name=action_event.tool_name,
                    tool_call_id=action_event.tool_call_id,
                    rejection_reason=reason,
                )
                self._on_event(rejection_event)
                logger.info(f"Rejected pending action: {action_event} - {reason}")

    def pause(self) -> None:
        """Pause agent execution.

        This method can be called from any thread to request that the agent
        pause execution. The pause will take effect at the next iteration
        of the run loop (between agent steps).

        Note: If called during an LLM completion, the pause will not take
        effect until the current LLM call completes.
        """

        if self.state.agent_status == AgentExecutionStatus.PAUSED:
            return

        with self.state:
            # Only pause when running or idle
            if (
                self.state.agent_status == AgentExecutionStatus.IDLE
                or self.state.agent_status == AgentExecutionStatus.RUNNING
            ):
                self.state.agent_status = AgentExecutionStatus.PAUSED
                pause_event = PauseEvent()
                self._on_event(pause_event)
                logger.info("Agent execution pause requested")

    def update_secrets(self, secrets: dict[str, SecretValue]) -> None:
        """Add secrets to the conversation.

        Args:
            secrets: Dictionary mapping secret keys to values or no-arg callables.
                     SecretValue = str | Callable[[], str]. Callables are invoked lazily
                     when a command references the secret key.
        """

        secrets_manager = self.state.secrets_manager
        secrets_manager.update_secrets(secrets)
        logger.info(f"Added {len(secrets)} secrets to conversation")

    def close(self) -> None:
        """Close the conversation and clean up all tool executors."""
        logger.debug("Closing conversation and cleaning up tool executors")
        for tool in self.agent.tools_map.values():
            if tool.executor is not None:
                try:
                    tool.executor.close()
                except Exception as e:
                    logger.warning(
                        f"Error closing executor for tool '{tool.name}': {e}"
                    )

    def __del__(self) -> None:
        """Ensure cleanup happens when conversation is destroyed."""
        try:
            self.close()
        except Exception as e:
            logger.warning(f"Error during conversation cleanup: {e}", exc_info=True)


class RemoteConversation(Conversation):
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
                "agent": agent.model_dump(),
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
        # Trigger a run on the server
        resp = self._client.post(
            f"/conversations/{self._id}/events/respond_to_confirmation",
            json={"accept": True, "reason": "User accepted"},
        )
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

    def set_confirmation_mode(self, enabled: bool) -> None:
        logger.warning(
            "RemoteConversation: set_confirmation_mode after start is not supported; "
            "set it on initialization instead."
        )

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

    def update_secrets(self, secrets: dict[str, SecretValue]) -> None:  # noqa: ARG002
        logger.warning(
            "RemoteConversation: update_secrets is not supported in remote mode."
        )

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
