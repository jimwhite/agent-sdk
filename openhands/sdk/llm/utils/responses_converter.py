"""Utilities for converting between ChatCompletions and Responses API formats."""

from typing import Any

from litellm.types.utils import ModelResponse

from openhands.sdk.llm.message import Message


def messages_to_responses_input(
    messages: list[dict[str, Any]] | list[Message],
) -> str:
    """Convert ChatCompletions messages format to Responses API input string.

    The Responses API uses a simple string input instead of the structured
    messages array used by ChatCompletions. This function converts the
    messages to a single string that captures the conversation context.

    Args:
        messages: List of messages in ChatCompletions format

    Returns:
        String input suitable for Responses API
    """
    if not messages:
        return ""

    # Convert Message objects to dicts if needed
    dict_messages: list[dict[str, Any]]
    if messages and isinstance(messages[0], Message):
        # Format messages directly to avoid circular import
        dict_messages = []
        for message in messages:
            if isinstance(message, Message):
                # Set basic capabilities for formatting
                message.cache_enabled = False
                message.vision_enabled = False
                message.function_calling_enabled = False
                dict_messages.append(message.to_llm_dict())
            else:
                dict_messages.append(message)
    else:
        dict_messages = messages  # type: ignore[assignment]

    # Convert messages to a single input string
    input_parts = []

    for msg in dict_messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            input_parts.append(f"System: {content}")
        elif role == "user":
            input_parts.append(f"User: {content}")
        elif role == "assistant":
            input_parts.append(f"Assistant: {content}")
        elif role == "tool":
            # Tool responses are included as context
            tool_call_id = msg.get("tool_call_id", "")
            input_parts.append(f"Tool Result ({tool_call_id}): {content}")

    return "\n\n".join(input_parts)


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
    # Extract the main content and reasoning content if available
    output_items = getattr(responses_result, "output", [])

    content = ""
    reasoning_content = ""

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
            elif item.type == "reasoning":
                # OpenAI Responses may include explicit reasoning items with `.content`
                try:
                    if hasattr(item, "content") and item.content:
                        reasoning_content = str(item.content)
                except Exception:
                    pass

    # Fallback to top-level reasoning.summary if no explicit block found
    if not reasoning_content:
        try:
            top_reasoning = getattr(responses_result, "reasoning", None)
            if top_reasoning is not None:
                # top_reasoning may be dict-like or pydantic model
                summary = getattr(top_reasoning, "summary", None)
                if summary is None and isinstance(top_reasoning, dict):
                    summary = top_reasoning.get("summary")
                if summary:
                    reasoning_content = str(summary)
        except Exception:
            pass

    # Create a ChatCompletions-compatible response
    message = {
        "role": "assistant",
        "content": content,
    }

    # Add reasoning content as a custom field if available
    if reasoning_content:
        message["reasoning_content"] = reasoning_content

    # Build the response structure with robust field coercion
    def _to_int(val, default: int = 0):
        try:
            if isinstance(val, bool):
                return int(val)
            if isinstance(val, (int, float)):
                return int(val)
            if isinstance(val, str) and val.isdigit():
                return int(val)
        except Exception:
            pass
        return default

    # created can be either `created` (int) or `created_at` (int). Avoid MagicMock.
    created_val = getattr(responses_result, "created", None)
    created = _to_int(created_val, default=-1)
    if created < 0:
        created = _to_int(getattr(responses_result, "created_at", None), default=0)

    model_val = getattr(responses_result, "model", "")
    model = (
        model_val
        if isinstance(model_val, str)
        else (str(model_val) if model_val is not None else "")
    )

    response = {
        "id": getattr(responses_result, "id", ""),
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": message,
                "finish_reason": "stop",
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
        try:
            usage = responses_result.usage
            response["usage"]["prompt_tokens"] = _to_int(
                getattr(usage, "input_tokens", 0), 0
            )
            response["usage"]["completion_tokens"] = _to_int(
                getattr(usage, "output_tokens", 0), 0
            )
            response["usage"]["total_tokens"] = _to_int(
                getattr(usage, "total_tokens", 0), 0
            )
            # Map Responses usage.output_tokens_details.reasoning_tokens
            # to ChatCompletions usage.completion_tokens_details.reasoning_tokens
            try:
                details = getattr(usage, "output_tokens_details", None)
                if details is None and isinstance(usage, dict):
                    details = usage.get("output_tokens_details")
                rt = None
                if details is not None:
                    try:
                        rt = getattr(details, "reasoning_tokens", None)
                    except Exception:
                        rt = None
                    if rt is None and isinstance(details, dict):
                        rt = details.get("reasoning_tokens")
                if rt is not None:
                    response["usage"]["completion_tokens_details"] = {
                        "reasoning_tokens": _to_int(rt, 0)
                    }
            except Exception:
                # Best-effort mapping; ignore if structure is unexpected
                pass

        except Exception:
            # Ignore malformed usage
            pass

    return ModelResponse(**response)
