from unittest.mock import MagicMock

from openhands.sdk.agent.base import AgentBase
from openhands.sdk.conversation import Conversation
from openhands.sdk.conversation.state import ConversationState
from openhands.sdk.conversation.types import ConversationCallbackType
from openhands.sdk.event.llm_convertible import MessageEvent, SystemPromptEvent
from openhands.sdk.llm import Message, TextContent


class DummyAgent(AgentBase):
    """A minimal agent that marks the conversation finished after it replies once."""

    def __init__(self):
        super().__init__(llm=MagicMock(name="LLM"), tools=[])
        self.prompt_manager = MagicMock()
        self.steps: int = 0

    def init_state(
        self, state: ConversationState, on_event: ConversationCallbackType
    ) -> None:
        event = SystemPromptEvent(
            source="agent", system_prompt=TextContent(text="dummy"), tools=[]
        )
        on_event(event)

    def step(
        self, state: ConversationState, on_event: ConversationCallbackType
    ) -> None:
        # Emit a trivial assistant message and finish the turn
        on_event(
            MessageEvent(
                source="agent",
                llm_message=Message(role="assistant", content=[TextContent(text="ok")]),
            )
        )
        state.agent_finished = True
        self.steps += 1


def test_followup_message_triggers_new_run_when_finished():
    agent = DummyAgent()
    convo = Conversation(agent=agent)

    # First user message and run
    convo.send_message(Message(role="user", content=[TextContent(text="do it")]))
    convo.run()
    assert agent.steps == 1

    # Simulate a follow-up user message being appended (e.g., from UI layer)
    # without going through Conversation.send_message()
    user_event = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="again")]),
    )
    convo._on_event(user_event)  # type: ignore[attr-defined]

    # Now run again; run() must reset finished state and process the new message
    convo.run()

    assert agent.steps == 2, "Agent should run again for the follow-up user message"
