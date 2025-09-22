from typing import Any
from unittest.mock import patch

from litellm.types.llms.openai import ResponsesAPIResponse
from pydantic import SecretStr

from openhands.sdk import LLM, Agent, Conversation, Message, TextContent


def _mk_agent():
    llm = LLM(model="openai/gpt-5-test", api_key=SecretStr("x"))
    return Agent(llm=llm, tools=[])


def _run(conv: Conversation):
    conv.send_message(message=Message(role="user", content=[TextContent(text="t")]))
    conv.run()


def test_parse_text_and_reasoning_and_tool_calls():
    agent = _mk_agent()
    conv = Conversation(agent=agent, callbacks=[])

    with patch("openhands.sdk.llm.llm.litellm_responses") as mock_responses:
        payload: dict[str, Any] = {
            "id": "resp_2",
            "created_at": 0,
            "model": "gpt-5-test",
            "output": [
                {
                    "type": "reasoning",
                    "id": "r",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "think 1"}],
                    "summary": [{"type": "summary_text", "text": "sum"}],
                },
                {
                    "type": "message",
                    "id": "m",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {"type": "output_text", "text": "final text"},
                        {"type": "output_text", "text": "more"},
                    ],
                },
                {
                    "type": "function_call",
                    "name": "finish",
                    "arguments": '{"message": "done"}',
                    "call_id": "tc_1",
                },
            ],
            "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        }
        mock_responses.return_value = ResponsesAPIResponse(**payload)

        _run(conv)

    # Last event should be an action (finish) queued and executed by Agent
    # We verify through conversation state: agent status should be FINISHED
    from openhands.sdk.conversation.state import AgentExecutionStatus

    assert conv.state.agent_status in {
        AgentExecutionStatus.FINISHED,
        AgentExecutionStatus.WAITING_FOR_CONFIRMATION,
    }


def test_parse_no_tools_message_only_reasoning():
    agent = _mk_agent()
    conv = Conversation(agent=agent, callbacks=[])

    with patch("openhands.sdk.llm.llm.litellm_responses") as mock_responses:
        payload: dict[str, Any] = {
            "id": "resp_3",
            "created_at": 0,
            "model": "gpt-5-test",
            "output": [
                {
                    "type": "reasoning",
                    "id": "r2",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": "internal"}],
                },
                {
                    "type": "message",
                    "id": "m2",
                    "role": "assistant",
                    "status": "completed",
                    "content": [
                        {"type": "output_text", "text": "hello"},
                    ],
                },
            ],
            "usage": {"input_tokens": 1, "output_tokens": 2, "total_tokens": 3},
        }
        mock_responses.return_value = ResponsesAPIResponse(**payload)

        _run(conv)

    # Conversation should have produced a terminal message event (no tools)
    from openhands.sdk.conversation.state import AgentExecutionStatus

    assert conv.state.agent_status == AgentExecutionStatus.FINISHED
