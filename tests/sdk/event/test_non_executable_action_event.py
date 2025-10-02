import json
from collections.abc import Sequence

from openhands.sdk.event.llm_convertible import NonExecutableActionEvent
from openhands.sdk.llm import MessageToolCall, TextContent


def test_non_executable_action_event_to_llm_message_round_trip() -> None:
    thought: Sequence[TextContent] = [TextContent(text="thinking...")]
    tc = MessageToolCall(
        id="call_xyz",
        name="missing_tool",
        arguments=json.dumps({"a": 1}),
        origin="completion",
    )

    evt = NonExecutableActionEvent(
        source="agent",
        thought=thought,
        reasoning_content="rc",
        thinking_blocks=[],
        tool_calls=[tc],
    )

    msg = evt.to_llm_message()
    assert msg.role == "assistant"
    assert msg.tool_calls is not None and len(msg.tool_calls) == 1
    assert msg.tool_calls[0].id == "call_xyz"
    assert msg.tool_calls[0].name == "missing_tool"
    assert len(msg.content) == 1 and isinstance(msg.content[0], TextContent)
    assert msg.content[0].text == "thinking..."
