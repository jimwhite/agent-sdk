"""OpenHands-native types for LLM interface abstraction.

This module provides OpenHands-native types that eliminate the need for
consumers to work directly with LiteLLM types, completing the abstraction
layer for the tool interface.
"""

from typing import Any

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from litellm.types.utils import ChatCompletionMessageToolCall
from pydantic import BaseModel

from openhands.sdk.tool.tool import ToolAnnotations


__all__ = ["OpenHandsToolSpec", "OpenHandsToolCall"]


class OpenHandsToolSpec(BaseModel):
    """OpenHands tool specification - consistent with existing patterns.

    This type provides a clean interface for tool specifications, exposing
    only OpenHands-native types to consumers while preserving the ability
    to convert to LiteLLM format internally.

    Attributes:
        name: The name of the tool
        description: A description of what the tool does
        parameters: The parameters schema for the tool
        annotations: Optional tool annotations for behavior hints
    """

    name: str
    description: str
    parameters: dict[str, Any]
    annotations: ToolAnnotations | None = None

    def to_litellm_format(self) -> ChatCompletionToolParam:
        """Internal conversion method - not exposed to agents.

        This method converts the OpenHands tool specification to the
        LiteLLM format required by the underlying completion API.
        """
        return ChatCompletionToolParam(
            type="function",
            function=ChatCompletionToolParamFunctionChunk(
                name=self.name,
                description=self.description,
                parameters=self.parameters,
            ),
        )


class OpenHandsToolCall(BaseModel):
    """OpenHands tool call - abstraction over LiteLLM tool call types.

    This type provides a clean interface for tool calls, exposing only
    OpenHands-native types to consumers while preserving compatibility
    with the underlying LiteLLM format.

    Attributes:
        id: The unique identifier for this tool call
        type: The type of tool call (typically "function")
        function: The function call details including name and arguments
    """

    id: str
    type: str
    function: dict[str, Any]

    @classmethod
    def from_litellm(
        cls, tool_call: ChatCompletionMessageToolCall
    ) -> "OpenHandsToolCall":
        """Create OpenHandsToolCall from LiteLLM tool call.

        This method converts from the LiteLLM format to our native format.
        """
        return cls(
            id=tool_call.id,
            type=tool_call.type,
            function={
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        )

    def to_litellm_format(self) -> ChatCompletionMessageToolCall:
        """Internal conversion method - not exposed to agents.

        This method converts the OpenHands tool call to the LiteLLM format
        required by the underlying completion API.
        """
        # This is a bit tricky since ChatCompletionMessageToolCall is a complex type
        # For now, we'll create a dict that matches the expected structure
        return ChatCompletionMessageToolCall(
            id=self.id,
            type=self.type,
            function={
                "name": self.function["name"],
                "arguments": self.function["arguments"],
            },
        )
