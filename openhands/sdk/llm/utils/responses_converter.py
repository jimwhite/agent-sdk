"""Utilities for converting Responses API results into Chat Completions format."""

from typing import Any

from litellm.types.utils import ModelResponse
from openai.types.responses.response import Response
from openai.types.responses.response_function_tool_call import ResponseFunctionToolCall
from openai.types.responses.response_output_message import ResponseOutputMessage
from openai.types.responses.response_output_refusal import ResponseOutputRefusal
from openai.types.responses.response_output_text import ResponseOutputText
from openai.types.responses.response_reasoning_item import ResponseReasoningItem


def responses_to_completion_format(
    responses_result: Response,
) -> ModelResponse:
    """Convert Responses API result to ChatCompletions format.

    This allows the Responses API result to be used with existing code
    that expects ChatCompletions format.

    Args:
        responses_result: Result from litellm.responses()

    Returns:
        ModelResponse in ChatCompletions format
    """
    # Extract the main content, tool calls, and reasoning content if available
    output_items = responses_result.output

    content = ""
    reasoning_content = ""
    tool_calls: list[dict[str, Any]] = []

    for item in output_items:
        if isinstance(item, ResponseOutputMessage):
            c = item.content
            if isinstance(c, list) and c:
                for seg in c:
                    if isinstance(seg, ResponseOutputText):
                        content = seg.text or content
                    elif isinstance(seg, ResponseOutputRefusal):
                        pass
            else:
                # Legacy fallback: older SDKs had content with `.text`
                if not isinstance(c, list) and hasattr(c, "text"):
                    content = c.text or content
        elif isinstance(item, ResponseFunctionToolCall):
            tool_calls.append(
                {
                    "id": item.call_id or "",
                    "type": "function",
                    "function": {
                        "name": item.name,
                        "arguments": item.arguments,
                    },
                }
            )
        elif isinstance(item, ResponseReasoningItem):
            # Prefer explicit content; fallback to summary
            if item.content:
                parts = [seg.text for seg in item.content if seg.text]
                if parts:
                    reasoning_content = "\n\n".join(parts)
            elif item.summary:
                parts = [s.text for s in item.summary if s.text]
                if parts:
                    reasoning_content = "\n\n".join(parts)

    # Create a ChatCompletions-compatible response
    message: dict[str, Any] = {
        "role": "assistant",
        "content": content,
    }
    if tool_calls:
        message["tool_calls"] = tool_calls

    # Add reasoning content as a custom field if available
    if reasoning_content:
        message["reasoning_content"] = reasoning_content

    # model string
    model = responses_result.model

    finish_reason = "tool_calls" if tool_calls else "stop"

    response = {
        "id": responses_result.id,
        "object": "chat.completion",
        "created": int(responses_result.created_at),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }

    # Extract usage information if available
    if hasattr(responses_result, "usage") and responses_result.usage is not None:
        usage = responses_result.usage
        # Map Responses API usage fields to ChatCompletions format
        response["usage"]["prompt_tokens"] = getattr(usage, "input_tokens", 0)
        response["usage"]["completion_tokens"] = getattr(usage, "output_tokens", 0)
        response["usage"]["total_tokens"] = getattr(usage, "total_tokens", 0)

        # Map reasoning tokens if available
        output_details = getattr(usage, "output_tokens_details", None)
        if output_details and hasattr(output_details, "reasoning_tokens"):
            reasoning_tokens = getattr(output_details, "reasoning_tokens", None)
            if reasoning_tokens is not None and isinstance(reasoning_tokens, int):
                response["usage"]["completion_tokens_details"] = {
                    "reasoning_tokens": reasoning_tokens
                }

    return ModelResponse(**response)
