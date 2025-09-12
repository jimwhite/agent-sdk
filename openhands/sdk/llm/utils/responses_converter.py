"""Utilities for converting Responses API results into Chat Completions format."""

from typing import Any

from litellm.types.utils import ModelResponse


def responses_to_completion_format(
    responses_result: Any,
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
    output_items = getattr(responses_result, "output", [])

    content = ""
    reasoning_content = ""
    tool_calls: list[dict[str, Any]] = []

    for item in output_items:
        if hasattr(item, "type"):
            if item.type == "message":
                # response.output.message.content can be list or object
                # depending on SDK version
                try:
                    if hasattr(item, "content"):
                        c = item.content
                        # Newer SDKs: content may be a list of segments
                        if isinstance(c, list) and c:
                            # Find output_text item
                            for seg in c:
                                if getattr(
                                    seg, "type", None
                                ) == "output_text" and hasattr(seg, "text"):
                                    content = getattr(seg, "text", "") or content
                        # Older / simplified: content has `.text`
                        elif hasattr(c, "text"):
                            content = getattr(c, "text", "") or content
                except Exception:
                    pass
            elif item.type == "function_call":
                # Map Responses function call to Chat Completions tool_call
                try:
                    name = getattr(item, "name", None)
                    arguments = getattr(item, "arguments", None)
                    call_id = getattr(item, "call_id", None)
                    tool_calls.append(
                        {
                            "id": call_id or "",
                            "type": "function",
                            "function": {
                                "name": name or "",
                                "arguments": arguments or "{}",
                            },
                        }
                    )
                except Exception:
                    pass
            elif item.type == "reasoning":
                # Surface reasoning content first, then fallback to summary
                try:
                    content_field = getattr(item, "content", None)
                    if isinstance(content_field, str) and content_field:
                        reasoning_content = content_field
                    elif hasattr(content_field, "text"):
                        rc = getattr(content_field, "text", None)
                        if rc:
                            reasoning_content = str(rc)
                    else:
                        summary = getattr(item, "summary", None)
                        if summary is not None:
                            try:
                                parts = []
                                for seg in summary:
                                    t = getattr(seg, "text", None)
                                    if t:
                                        parts.append(str(t))
                                if parts:
                                    reasoning_content = "\n\n".join(parts)
                            except Exception:
                                reasoning_content = str(summary)
                except Exception:
                    pass

    # Create a ChatCompletions-compatible response
    message = {
        "role": "assistant",
        "content": content,
    }
    if tool_calls:
        message["tool_calls"] = tool_calls

    # Add reasoning content as a custom field if available
    if reasoning_content:
        message["reasoning_content"] = reasoning_content

    # created timestamp from Responses API (created_at)
    created = int(getattr(responses_result, "created_at"))

    # model can be a string or another type; normalize to string
    model_val = getattr(responses_result, "model", "")
    model = (
        model_val
        if isinstance(model_val, str)
        else (str(model_val) if model_val is not None else "")
    )

    finish_reason = "tool_calls" if tool_calls else "stop"

    response = {
        "id": getattr(responses_result, "id", ""),
        "object": "chat.completion",
        "created": created,
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
