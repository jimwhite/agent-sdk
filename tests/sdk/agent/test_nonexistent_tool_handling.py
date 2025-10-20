"""Test agent behavior when calling non-existent tools."""

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
from openhands.sdk.conversation.state import AgentExecutionStatus
from openhands.sdk.event import AgentErrorEvent, MessageEvent
from openhands.sdk.llm import LLM, Message, TextContent


def test_nonexistent_tool_returns_error_and_continues_conversation():
    """Test that calling a non-existent tool returns AgentErrorEvent and continues conversation."""  # noqa: E501

    # Create a simple agent with no custom tools (only built-in ones)
    llm = LLM(
        usage_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])

    # Mock LLM responses
    def mock_llm_response(messages, **kwargs):
        # First response: Agent tries to call a non-existent tool
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
                                id="call_1",
                                type="function",
                                function=Function(
                                    name="nonexistent_tool",
                                    arguments='{"param": "value"}',
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

    # Collect events from the conversation
    collected_events = []

    def event_callback(event):
        collected_events.append(event)

    # Create conversation and run with mocked LLM
    conversation = Conversation(agent=agent, callbacks=[event_callback])

    with patch(
        "openhands.sdk.llm.llm.litellm_completion", side_effect=mock_llm_response
    ):
        # Send a message to start the conversation
        conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text="Please help me with something.")],
            )
        )

        # Run one step to trigger the tool call
        agent.step(conversation.state, on_event=event_callback)

    # Verify that an AgentErrorEvent was generated
    error_events = [e for e in collected_events if isinstance(e, AgentErrorEvent)]
    assert len(error_events) == 1, (
        f"Expected 1 AgentErrorEvent, got {len(error_events)}"
    )

    error_event = error_events[0]
    assert "nonexistent_tool" in error_event.error
    assert "not found" in error_event.error
    assert error_event.tool_name == "nonexistent_tool"
    assert error_event.tool_call_id == "call_1"

    # Verify that the conversation is NOT finished (this is the key fix)
    with conversation.state:
        assert conversation.state.agent_status != AgentExecutionStatus.FINISHED, (
            "Agent should not be finished after encountering non-existent tool"
        )

    # Verify that the error event is properly formatted for LLM
    llm_message = error_event.to_llm_message()
    assert llm_message.role == "tool"
    assert llm_message.tool_call_id == "call_1"
    content_text = llm_message.content[0]
    assert isinstance(content_text, TextContent)
    assert "nonexistent_tool" in content_text.text
    assert "not found" in content_text.text


def test_nonexistent_tool_error_includes_available_tools():
    """Test that the error message includes available tools."""

    # Create agent with some tools
    llm = LLM(
        usage_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])  # Only built-in tools

    # Mock LLM response that calls non-existent tool
    def mock_llm_response(messages, **kwargs):
        return ModelResponse(
            id="mock-response-1",
            choices=[
                Choices(
                    index=0,
                    message=LiteLLMMessage(
                        role="assistant",
                        content="I'll use a non-existent tool.",
                        tool_calls=[
                            ChatCompletionMessageToolCall(
                                id="call_1",
                                type="function",
                                function=Function(
                                    name="missing_tool",
                                    arguments="{}",
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

    collected_events = []

    def event_callback(event):
        collected_events.append(event)

    conversation = Conversation(agent=agent, callbacks=[event_callback])

    with patch(
        "openhands.sdk.llm.llm.litellm_completion", side_effect=mock_llm_response
    ):
        conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text="Test message")],
            )
        )
        agent.step(conversation.state, on_event=event_callback)

    # Find the error event
    error_events = [e for e in collected_events if isinstance(e, AgentErrorEvent)]
    assert len(error_events) == 1

    error_event = error_events[0]

    # Verify error message includes available tools
    assert "missing_tool" in error_event.error
    assert "not found" in error_event.error
    assert "Available:" in error_event.error

    # Should include built-in tools like 'finish' and 'think'
    assert "finish" in error_event.error
    assert "think" in error_event.error


def test_conversation_continues_after_tool_error():
    """Test that conversation can continue after a tool error."""

    llm = LLM(
        usage_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])

    call_count = 0

    def mock_llm_response(messages, **kwargs):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # First call: try non-existent tool
            return ModelResponse(
                id="mock-response-1",
                choices=[
                    Choices(
                        index=0,
                        message=LiteLLMMessage(
                            role="assistant",
                            content="I'll try a non-existent tool first.",
                            tool_calls=[
                                ChatCompletionMessageToolCall(
                                    id="call_1",
                                    type="function",
                                    function=Function(
                                        name="bad_tool",
                                        arguments="{}",
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
        else:
            # Second call: respond normally after seeing the error
            return ModelResponse(
                id="mock-response-2",
                choices=[
                    Choices(
                        index=0,
                        message=LiteLLMMessage(
                            role="assistant",
                            content=(
                                "I see there was an error. Let me respond normally now."
                            ),
                        ),
                        finish_reason="stop",
                    )
                ],
                created=0,
                model="test-model",
                object="chat.completion",
            )

    collected_events = []

    def event_callback(event):
        collected_events.append(event)

    conversation = Conversation(agent=agent, callbacks=[event_callback])

    with patch(
        "openhands.sdk.llm.llm.litellm_completion", side_effect=mock_llm_response
    ):
        conversation.send_message(
            Message(
                role="user",
                content=[TextContent(text="Please help me.")],
            )
        )

        # Run first step - should generate error
        agent.step(conversation.state, on_event=event_callback)

        # Verify we got an error event
        error_events = [e for e in collected_events if isinstance(e, AgentErrorEvent)]
        assert len(error_events) == 1

        # Verify conversation is not finished
        with conversation.state:
            assert conversation.state.agent_status != AgentExecutionStatus.FINISHED

        # Run second step - should continue normally
        agent.step(conversation.state, on_event=event_callback)

        # Verify we got a message event from the second response
        message_events = [
            e
            for e in collected_events
            if isinstance(e, MessageEvent) and e.source == "agent"
        ]
        assert len(message_events) == 1

        message_event = message_events[0]
        content_text = message_event.llm_message.content[0]
        assert isinstance(content_text, TextContent)
        assert "respond normally" in content_text.text

        # Now the conversation should be finished
        with conversation.state:
            assert conversation.state.agent_status == AgentExecutionStatus.FINISHED

    # Verify we made two LLM calls
    assert call_count == 2
