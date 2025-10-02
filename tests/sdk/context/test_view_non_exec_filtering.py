import json

from openhands.sdk.context.view import View
from openhands.sdk.event.llm_convertible import (
    AgentErrorEvent,
    MessageEvent,
    NonExecutableActionEvent,
)
from openhands.sdk.llm import Message, MessageToolCall, TextContent


def test_filter_keeps_non_exec_when_matched_by_observation() -> None:
    # NonExecutableActionEvent with a tool_call id
    tc = MessageToolCall(
        id="call_keep_me",
        name="missing_tool",
        arguments=json.dumps({}),
        origin="completion",
    )
    nea = NonExecutableActionEvent(
        source="agent",
        thought=[TextContent(text="...")],
        tool_call=tc,
    )

    # Matching AgentErrorEvent (observation path)
    err = AgentErrorEvent(
        source="agent",
        error="not found",
        tool_name="missing_tool",
        tool_call_id="call_keep_me",
    )

    # Noise message events
    m1 = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="hi")]),
    )
    m2 = MessageEvent(
        source="user",
        llm_message=Message(role="user", content=[TextContent(text="bye")]),
    )

    events = [m1, nea, err, m2]

    filtered = View.filter_unmatched_tool_calls(events)  # type: ignore[arg-type]

    # Both NonExecutableActionEvent and matching AgentErrorEvent must be kept
    assert len(filtered) == 4
    assert nea in filtered
    assert err in filtered
    assert m1 in filtered and m2 in filtered
