# openhands.sdk.conversation.conversation

## Classes

### Conversation

Main conversation handler for agent interactions.

#### Functions

##### pause(self) -> None

Pause agent execution.

This method can be called from any thread to request that the agent
pause execution. The pause will take effect at the next iteration
of the run loop (between agent steps).

Note: If called during an LLM completion, the pause will not take
effect until the current LLM call completes.

##### reject_pending_actions(self, reason: str = 'User rejected the action') -> None

Reject all pending actions from the agent.

This is a non-invasive method to reject actions between run() calls.
Also clears the agent_waiting_for_confirmation flag.

##### run(self) -> None

Runs the conversation until the agent finishes.

In confirmation mode:
- First call: creates actions but doesn't execute them, stops and waits
- Second call: executes pending actions (implicit confirmation)

In normal mode:
- Creates and executes actions immediately

Can be paused between steps

##### send_message(self, message: openhands.sdk.llm.message.Message) -> None

Sending messages to the agent.

##### set_confirmation_mode(self, enabled: bool) -> None

Enable or disable confirmation mode and store it in conversation state.

## Functions

### compose_callbacks(callbacks: Iterable[Callable[[Annotated[openhands.sdk.event.base.EventBase, DiscriminatedUnion[EventBase]]], NoneType]]) -> Callable[[Annotated[openhands.sdk.event.base.EventBase, DiscriminatedUnion[EventBase]]], NoneType]

Compose multiple callbacks into a single callback function.

