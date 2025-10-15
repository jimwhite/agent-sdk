from openhands.sdk.event.base import _combine_action_events
from openhands.sdk.event.llm_convertible.action import ActionEvent
from openhands.sdk.llm import MessageToolCall, ReasoningItemModel, TextContent


def _make_action_event(
    *,
    tool_call_id: str,
    tool_name: str,
    llm_response_id: str,
    thought_text: str | None = None,
    responses_reasoning_item: ReasoningItemModel | None = None,
) -> ActionEvent:
    thought = [TextContent(text=thought_text)] if thought_text else []
    tool_call = MessageToolCall(
        id=tool_call_id,
        name=tool_name,
        arguments="{}",
        origin="responses",
    )
    return ActionEvent(
        thought=thought,
        reasoning_content=None,
        thinking_blocks=[],
        responses_reasoning_item=responses_reasoning_item,
        action=None,
        tool_name=tool_name,
        tool_call_id=tool_call_id,
        tool_call=tool_call,
        llm_response_id=llm_response_id,
    )


def test_combine_action_events_preserves_responses_reasoning_item():
    ri = ReasoningItemModel(
        id="rid",
        summary=["summary"],
        content=["content"],
        encrypted_content="enc",
        status="completed",
    )

    e1 = _make_action_event(
        tool_call_id="fc_call_1",
        tool_name="tool_one",
        llm_response_id="resp-123",
        thought_text="first tool",
        responses_reasoning_item=ri,
    )
    e2 = _make_action_event(
        tool_call_id="fc_call_2",
        tool_name="tool_two",
        llm_response_id="resp-123",
    )

    combined = _combine_action_events([e1, e2])

    assert combined.responses_reasoning_item is ri
    assert combined.tool_calls is not None
    assert len(combined.tool_calls) == 2
    assert {tc.id for tc in combined.tool_calls} == {"fc_call_1", "fc_call_2"}
