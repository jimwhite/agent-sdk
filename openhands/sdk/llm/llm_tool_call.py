import json
from typing import Any, Literal

from litellm import ChatCompletionMessageToolCall, ResponseFunctionToolCall
from pydantic import BaseModel, Field


class _FunctionView:
    def __init__(self, name: str, arguments: str) -> None:
        self.name = name
        self.arguments = arguments


class LLMToolCall(BaseModel):
    """Transport-agnostic tool call representation.

    One canonical id is used for linking across actions/observations and
    for Responses function_call_output call_id.
    """

    id: str = Field(..., description="Canonical tool call id")
    name: str = Field(..., description="Tool/function name")
    arguments_json: str = Field(..., description="JSON string of arguments")
    origin: Literal["completion", "responses"] = Field(
        ..., description="Originating API family"
    )

    @property
    def function(self) -> _FunctionView:
        # Backward-compat view for tests expecting OpenAI shape
        return _FunctionView(self.name, self.arguments_json)

    raw: ChatCompletionMessageToolCall | ResponseFunctionToolCall | None = Field(
        default=None,
        description="Original provider object for advanced consumers",
        exclude=True,
    )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LLMToolCall):
            return NotImplemented
        return (
            self.id == other.id
            and self.name == other.name
            and self.arguments_json == other.arguments_json
            and self.origin == other.origin
        )

    @classmethod
    def from_provider_call(
        cls, item: Any, *, origin: Literal["completion", "responses"] | None = None
    ) -> "LLMToolCall":
        """Normalize a provider tool call (dict or object) into LLMToolCall.

        - Supports OpenAI Chat Completions tool call shapes
          (ChatCompletionMessageToolCall or dict with {id, function:{name, arguments}})
        - Supports Responses tool call shapes (ResponseFunctionToolCall or dict with
          {type: "function_call", call_id, name, arguments})
        - If origin isn't provided, it is inferred from the object type or dict shape
        """
        # Pass-through
        if isinstance(item, LLMToolCall):
            return item

        # Determine origin when not explicitly provided
        inferred_origin: Literal["completion", "responses"] = (
            origin if origin is not None else "completion"
        )
        try:
            if isinstance(item, ResponseFunctionToolCall):
                inferred_origin = "responses"
            elif isinstance(item, ChatCompletionMessageToolCall):
                inferred_origin = "completion"
            elif isinstance(item, dict):
                # Heuristic: Responses dicts commonly have type=="function_call"
                # and fields name/arguments/call_id; ChatCompletions have
                # function:{name, arguments} and id
                t = item.get("type")
                if t == "function_call" or ("call_id" in item and "name" in item):
                    inferred_origin = "responses"
                elif "function" in item or "id" in item:
                    inferred_origin = "completion"
        except Exception:
            pass

        # Extract fields
        call_id: str | None = None
        name: str | None = None
        args: Any = None

        if isinstance(item, ChatCompletionMessageToolCall):
            call_id = getattr(item, "id", None)
            fn = getattr(item, "function", None)
            if fn is not None:
                name = getattr(fn, "name", None)
                args = getattr(fn, "arguments", None)
            safe_raw: (
                ChatCompletionMessageToolCall | ResponseFunctionToolCall | None
            ) = item
        elif isinstance(item, ResponseFunctionToolCall):
            call_id = getattr(item, "call_id", None)
            name = getattr(item, "name", None)
            args = getattr(item, "arguments", None)
            safe_raw = item
        elif isinstance(item, dict):
            # Chat Completions dict shape
            fn = item.get("function")
            if isinstance(fn, dict):
                name = fn.get("name")
                args = fn.get("arguments")
            # Responses dict shape
            if name is None:
                name = item.get("name")
            if args is None:
                args = item.get("arguments")

            call_id = item.get("id") or item.get("call_id")
            safe_raw = None
        else:
            # Unknown type; best-effort stringification
            call_id = None
            name = None
            args = None
            safe_raw = None

        # Normalize arguments -> JSON string
        if args is None:
            args_str = "{}"
        elif isinstance(args, str):
            args_str = args
        else:
            try:
                args_str = json.dumps(args)
            except Exception:
                args_str = str(args)

        # Fallbacks
        call_id = call_id or "toolu_0"
        name = name or "unknown_function"

        return cls(
            id=str(call_id),
            name=str(name),
            arguments_json=args_str,
            origin=inferred_origin,
            raw=safe_raw,
        )
