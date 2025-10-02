"""Tests that the agent emits NonExecutableActionEvent on missing tools."""

import json
from unittest.mock import patch

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import (
    Choices,
    Function,
    Message as LiteLLMMessage,
    ModelResponse,
)
from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.event.llm_convertible import (
    AgentErrorEvent,
    MessageEvent,
    NonExecutableActionEvent,
)
from openhands.sdk.llm import LLM, Message, TextContent


def test_emits_non_executable_action_event_then_error_on_missing_tool() -> None:
    llm = LLM(
        service_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])

    def mock_llm_response(messages, **kwargs):
        return ModelResponse(
            id="mock-response-1",
            choices=[
                Choices(
                    index=0,
                    message=LiteLLMMessage(
                        role="assistant",
                        content="I'll use a non-existent tool to help you.",
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="call_x",
                                type="function",
                                function=Function(
                                    name="nonexistent_tool",
                                    arguments=json.dumps({"param": "value"}),
                                ),
                            )
                        ],
                    ),
                    finish_reason="tool_calls",
                )
            ],
            created=0,
            model="test-model",
            object="chat.completion",
        )

    collected = []

    def cb(e):
        collected.append(e)

    conv = Conversation(agent=agent, callbacks=[cb])

    with patch(
        "openhands.sdk.llm.llm.litellm_completion", side_effect=mock_llm_response
    ):
        conv.send_message(Message(role="user", content=[TextContent(text="go")]))
        agent.step(conv.state, on_event=cb)

    # We expect a NonExecutableActionEvent followed by an AgentErrorEvent
    types = [type(e) for e in collected]
    assert NonExecutableActionEvent in types
    assert AgentErrorEvent in types

    # Ensure ordering: NEA occurs before AgentErrorEvent for same call id
    first_nea_idx = next(
        i for i, e in enumerate(collected) if isinstance(e, NonExecutableActionEvent)
    )
    first_err_idx = next(
        i for i, e in enumerate(collected) if isinstance(e, AgentErrorEvent)
    )
    assert first_nea_idx < first_err_idx

    # Verify tool_call_id continuity
    nea = next(e for e in collected if isinstance(e, NonExecutableActionEvent))
    assert len(nea.tool_calls) == 1
    tc_id = nea.tool_calls[0].id
    err = next(e for e in collected if isinstance(e, AgentErrorEvent))
    assert err.tool_call_id == tc_id

    # Ensure message event exists for the initial system prompt
    assert any(isinstance(e, MessageEvent) for e in collected)
