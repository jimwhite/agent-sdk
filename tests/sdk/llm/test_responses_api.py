"""Tests for non-streaming Responses API integration (GPT-5 family).

Covers:
- Routing by model (Agent calls LLM.responses)
- previous_response_id propagation across turns
- Strict mismatch error when previous_response_id set on non-supported model
- Tool-calls and reasoning parsing on LLM.responses
- Telemetry usage mapping on LLM.responses
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from litellm.types.utils import Usage
from pydantic import SecretStr

from openhands.sdk import LLM, Agent, Conversation, Message, TextContent


class FakeResponsesObj:
    """Minimal object mimicking OpenAI Responses output used by litellm.responses.

    Attributes accessed by LLM.responses:
    - id: str
    - output_text: str | None
    - output: list[Any] | None
    - usage: Optional[Usage] (for telemetry)
    """

    def __init__(
        self,
        *,
        id: str = "resp_1",
        output_text: str | None = "Hello",
        output: list[Any] | None = None,
        usage: Usage | None = None,
    ) -> None:
        self.id = id
        self.output_text = output_text
        self.output = output or []
        self.usage = usage


class _FnCall:
    def __init__(self, call_id: str, name: str, arguments: str) -> None:
        self.type = "function_call"
        self.call_id = call_id
        self.name = name
        self.arguments = arguments


class _Reasoning:
    def __init__(
        self,
        summary_texts: list[str] | None = None,
        content_texts: list[str] | None = None,
    ) -> None:
        self.type = "reasoning"
        self.summary = [type("T", (), {"text": t}) for t in (summary_texts or [])]
        self.content = [type("T", (), {"text": t}) for t in (content_texts or [])]


@patch("openhands.sdk.llm.llm.litellm.responses")
def test_agent_routes_to_responses_and_sets_previous_id(mock_responses):
    # Arrange: mock a simple text response (no tool-calls)
    mock_responses.return_value = FakeResponsesObj(id="resp_1", output_text="Hi")

    llm = LLM(model="gpt-5", service_id="test-llm", api_key=SecretStr("k"))
    agent = Agent(llm=llm, tools=[])
    conv = Conversation(agent=agent)

    conv.send_message(Message(role="user", content=[TextContent(text="Hello")]))

    # Act
    conv.run()

    # Assert: LLM.responses called once; state.previous_response_id set
    assert mock_responses.call_count == 1
    kwargs = mock_responses.call_args.kwargs
    assert kwargs.get("model") == "gpt-5"
    assert (
        "previous_response_id" not in kwargs or kwargs["previous_response_id"] is None
    )
    assert conv.state.previous_response_id == "resp_1"


@patch("openhands.sdk.llm.llm.litellm.responses")
def test_previous_response_id_propagates_to_next_turn(mock_responses):
    # First turn -> resp_1, second turn -> resp_2
    mock_responses.side_effect = [
        FakeResponsesObj(id="resp_1", output_text="Step1"),
        FakeResponsesObj(id="resp_2", output_text="Step2"),
    ]

    llm = LLM(model="gpt-5-mini", service_id="test-llm", api_key=SecretStr("k"))
    agent = Agent(llm=llm, tools=[])
    conv = Conversation(agent=agent)

    # First user turn
    conv.send_message(Message(role="user", content=[TextContent(text="Hi")]))
    conv.run()
    assert conv.state.previous_response_id == "resp_1"

    # Second user turn (new message) should include previous_response_id
    conv.send_message(Message(role="user", content=[TextContent(text="Next")]))
    conv.run()

    assert conv.state.previous_response_id == "resp_2"
    # Verify second call included previous_response_id="resp_1"
    assert mock_responses.call_count == 2
    second_kwargs = mock_responses.call_args_list[1].kwargs
    assert second_kwargs.get("previous_response_id") == "resp_1"


def test_strict_mismatch_error_on_non_supported_model_with_prev_id():
    # No patch needed; error is raised before transport call
    llm = LLM(model="gpt-4o", service_id="test-llm", api_key=SecretStr("k"))
    agent = Agent(llm=llm, tools=[])
    conv = Conversation(agent=agent)

    # Seed previous_response_id manually to simulate continuation on non-supported model
    conv.state.previous_response_id = "resp_999"
    conv.send_message(Message(role="user", content=[TextContent(text="Hello")]))

    with pytest.raises(
        RuntimeError,
        match="previous_response_id is set but model lacks Responses support",
    ):
        conv.run()


@patch("openhands.sdk.llm.llm.litellm.responses")
def test_llm_responses_parses_tool_calls_and_reasoning(mock_responses):
    # Arrange: function-call + reasoning blocks
    items = [
        _FnCall(call_id="call_1", name="echo", arguments='{"text":"hi"}'),
        _Reasoning(summary_texts=["plan"], content_texts=["think1", "think2"]),
    ]
    mock_responses.return_value = FakeResponsesObj(
        id="resp_1", output_text="ok", output=items
    )

    llm = LLM(model="gpt-5", service_id="test-llm", api_key=SecretStr("k"))

    # Act
    out = llm.responses(instructions="sys", inputs=[], tools=None)

    # Assert
    msg = out.message
    assert msg.tool_calls is not None and len(msg.tool_calls) == 1
    tc = msg.tool_calls[0]
    assert (
        tc.id == "call_1" and tc.name == "echo" and tc.arguments_json == '{"text":"hi"}'
    )
    assert msg.reasoning_content is not None
    assert "plan" in msg.reasoning_content and "think1" in msg.reasoning_content


@patch("openhands.sdk.llm.llm.litellm.responses")
def test_llm_responses_telemetry_usage_mapping(mock_responses):
    usage = Usage(prompt_tokens=7, completion_tokens=3, total_tokens=10)
    mock_responses.return_value = FakeResponsesObj(
        id="resp_tele", output_text="x", usage=usage
    )

    llm = LLM(model="gpt-5", service_id="test-llm", api_key=SecretStr("k"))

    _ = llm.responses(instructions="sys", inputs=[], tools=None)

    # Telemetry should have recorded a token usage entry
    m = llm.metrics
    assert len(m.token_usages) >= 1
    last = m.token_usages[-1]
    assert last.prompt_tokens == 7
    assert last.completion_tokens == 3
