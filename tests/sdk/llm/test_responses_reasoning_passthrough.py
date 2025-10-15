from openhands.sdk.llm import (
    LLM,
    Message,
    MessageToolCall,
    ReasoningItemModel,
    TextContent,
)


def test_responses_reasoning_item_reemitted_in_next_request_formatting():
    llm = LLM(model="gpt-5-mini")

    system = Message(role="system", content=[TextContent(text="You are helpful.")])
    user = Message(role="user", content=[TextContent(text="Call the tool.")])

    reasoning = ReasoningItemModel(
        id="ri_123",
        summary=["thinking summary"],
        content=["thinking details"],
        encrypted_content="encrypted-payload",
        status="completed",
    )

    tool_call = MessageToolCall(
        id="fc_call_1",
        name="demo_tool",
        arguments="{}",
        origin="responses",
    )

    assistant = Message(
        role="assistant",
        content=[TextContent(text="Calling demo_tool...")],
        tool_calls=[tool_call],
        responses_reasoning_item=reasoning,
    )

    tool_result = Message(
        role="tool",
        tool_call_id=tool_call.id,
        name=tool_call.name,
        content=[TextContent(text='{"ok": true}')],
    )

    instructions, input_items = llm.format_messages_for_responses(
        [system, user, assistant, tool_result]
    )

    assert instructions == "You are helpful."

    reasoning_items = [item for item in input_items if item.get("type") == "reasoning"]
    assert len(reasoning_items) == 1
    reasoning_entry = reasoning_items[0]

    assert reasoning_entry["id"] == "ri_123"
    assert [seg["text"] for seg in reasoning_entry.get("summary", [])] == [
        "thinking summary"
    ]
    assert [seg["text"] for seg in reasoning_entry.get("content", [])] == [
        "thinking details"
    ]
    assert reasoning_entry.get("encrypted_content") == "encrypted-payload"
    assert reasoning_entry.get("status") == "completed"

    function_call_items = [
        item for item in input_items if item.get("type") == "function_call"
    ]
    assert len(function_call_items) == 1
    assert function_call_items[0]["call_id"].startswith("fc_")

    function_output_items = [
        item for item in input_items if item.get("type") == "function_call_output"
    ]
    assert len(function_output_items) == 1
    assert function_output_items[0]["call_id"] == function_call_items[0]["call_id"]
    assert function_output_items[0]["output"] == '{"ok": true}'
