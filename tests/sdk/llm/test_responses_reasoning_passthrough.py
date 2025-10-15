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


def test_responses_function_call_outputs_follow_calls():
    llm = LLM(model="gpt-5-mini")

    tool_call_one = MessageToolCall(
        id="fc_call_one",
        name="first",
        arguments="{}",
        origin="responses",
    )
    tool_call_two = MessageToolCall(
        id="fc_call_two",
        name="second",
        arguments="{}",
        origin="responses",
    )

    assistant = Message(
        role="assistant",
        content=[TextContent(text="running tools")],
        tool_calls=[tool_call_one, tool_call_two],
    )

    tool_result_one = Message(
        role="tool",
        tool_call_id=tool_call_one.id,
        name=tool_call_one.name,
        content=[TextContent(text="first output")],
    )
    tool_result_two = Message(
        role="tool",
        tool_call_id=tool_call_two.id,
        name=tool_call_two.name,
        content=[TextContent(text="second output")],
    )

    _, input_items = llm.format_messages_for_responses(
        [assistant, tool_result_one, tool_result_two]
    )

    function_calls = [
        item for item in input_items if item.get("type") == "function_call"
    ]
    outputs = [
        item for item in input_items if item.get("type") == "function_call_output"
    ]

    assert [fc["call_id"] for fc in function_calls] == [
        "fc_call_one",
        "fc_call_two",
    ]

    assert [out["call_id"] for out in outputs] == [
        "fc_call_one",
        "fc_call_two",
    ]

    # Ensure ordering interleaves call/output for each tool
    call_indices = [input_items.index(fc) for fc in function_calls]
    output_indices = [input_items.index(out) for out in outputs]
    for call_idx, output_idx in zip(call_indices, output_indices):
        assert output_idx == call_idx + 1
