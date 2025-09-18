"""MCPTool definition and implementation."""

import json
from collections.abc import Sequence

import mcp.types
from rich.text import Text

from openhands.sdk.llm import ImageContent, TextContent
from openhands.sdk.logger import get_logger
from openhands.sdk.tool.schema import Schema, SchemaField, SchemaInstance
from openhands.sdk.utils import to_camel_case
from openhands.sdk.utils.visualize import display_dict


logger = get_logger(__name__)


# NOTE: We don't define MCPToolAction because it
# will be dynamically created from the MCP tool schema.


def make_mcp_observation_schema() -> Schema:
    """Create schema for MCP tool observations."""
    from typing import Union

    return Schema(
        type="observation",
        fields=[
            SchemaField.create(
                name="content",
                description=(
                    "List of content blocks (text or image) returned from the MCP tool"
                ),
                type=list[Union[TextContent, ImageContent]],
                required=True,
            ),
            SchemaField.create(
                name="is_error",
                description="Whether the call resulted in an error",
                type=bool,
                required=True,
            ),
            SchemaField.create(
                name="tool_name",
                description="Name of the tool that was called",
                type=str,
                required=True,
            ),
        ],
    )


class MCPToolObservation:
    """Observation from MCP tool execution."""

    @classmethod
    def from_call_tool_result(
        cls, tool_name: str, result: mcp.types.CallToolResult
    ) -> SchemaInstance:
        """Create an MCPToolObservation SchemaInstance from a CallToolResult."""
        content: list[mcp.types.ContentBlock] = result.content
        converted_content = []
        for block in content:
            if isinstance(block, mcp.types.TextContent):
                converted_content.append(TextContent(text=block.text))
            elif isinstance(block, mcp.types.ImageContent):
                converted_content.append(
                    ImageContent(
                        image_urls=[f"data:{block.mimeType};base64,{block.data}"],
                    )
                )
            else:
                logger.warning(
                    f"Unsupported MCP content block type: {type(block)}. Ignoring."
                )

        return SchemaInstance(
            name=f"MCP{to_camel_case(tool_name)}Observation",
            definition=make_mcp_observation_schema(),
            data={
                "content": converted_content,
                "is_error": result.isError,
                "tool_name": tool_name,
            },
        )

    @staticmethod
    def agent_observation(
        observation: SchemaInstance,
    ) -> Sequence[TextContent | ImageContent]:
        """Format the observation for agent display."""
        tool_name = observation.data.get("tool_name", "unknown")
        is_error = observation.data.get("is_error", False)
        content = observation.data.get("content", [])

        initial_message = f"[Tool '{tool_name}' executed.]\n"
        if is_error:
            initial_message += "[An error occurred during execution.]\n"
        return [TextContent(text=initial_message)] + content

    @staticmethod
    def visualize(observation: SchemaInstance) -> Text:
        """Return Rich Text representation of this observation."""
        tool_name = observation.data.get("tool_name", "unknown")
        is_error = observation.data.get("is_error", False)
        content_blocks = observation.data.get("content", [])

        content = Text()
        content.append(f"[MCP Tool '{tool_name}' Observation]\n", style="bold")
        if is_error:
            content.append("[Error during execution]\n", style="bold red")
        for block in content_blocks:
            if isinstance(block, TextContent):
                # try to see if block.text is a JSON
                try:
                    parsed = json.loads(block.text)
                    content.append(display_dict(parsed))
                    continue
                except (json.JSONDecodeError, TypeError):
                    content.append(block.text + "\n")
            elif isinstance(block, ImageContent):
                content.append(f"[Image with {len(block.image_urls)} URLs]\n")
        return content
