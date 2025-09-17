"""Utility functions for MCP integration."""

import re

import mcp.types
from pydantic import Field, ValidationError, computed_field

from openhands.sdk.llm import TextContent
from openhands.sdk.logger import get_logger
from openhands.sdk.mcp import MCPToolObservation
from openhands.sdk.mcp.client import MCPClient
from openhands.sdk.tool import Tool, ToolAnnotations, ToolExecutor
from openhands.sdk.tool.schema import Schema, SchemaField, SchemaInstance


logger = get_logger(__name__)


# NOTE: We don't define MCPToolAction because it
# will be a pydantic BaseModel dynamically created from the MCP tool schema.
# It will be available as "tool.action_type".


def to_camel_case(s: str) -> str:
    parts = re.split(r"[_\-\s]+", s)
    return "".join(word.capitalize() for word in parts if word)


def mcp_schema_to_schema(name: str, mcp_schema: dict) -> Schema:
    """Convert MCP JSON schema to our Schema format."""
    fields = []

    if "properties" in mcp_schema:
        required_fields = set(mcp_schema.get("required", []))

        for field_name, field_def in mcp_schema["properties"].items():
            field_type = field_def.get("type", "string")
            description = field_def.get("description", f"Field {field_name}")

            # Convert JSON schema type to our SchemaFieldType
            if field_type == "string":
                schema_type = str
            elif field_type == "integer":
                schema_type = int
            elif field_type == "number":
                schema_type = float
            elif field_type == "boolean":
                schema_type = bool
            elif field_type == "array":
                schema_type = list
            elif field_type == "object":
                schema_type = dict
            else:
                schema_type = str  # fallback

            fields.append(
                SchemaField.create(
                    name=field_name,
                    description=description,
                    type=schema_type,
                    required=field_name in required_fields,
                )
            )

    # Always add security_risk field to input schemas
    if ".input" in name:
        fields.append(
            SchemaField.create(
                name="security_risk",
                description="The LLM's assessment of the safety risk of this "
                "action. See the SECURITY_RISK_ASSESSMENT section in the system "
                "prompt for risk level definitions.",
                type=str,
                required=True,
                enum=["LOW", "MEDIUM", "HIGH", "UNKNOWN"],
            )
        )

    return Schema(name=name, fields=fields)


class MCPToolExecutor(ToolExecutor):
    """Executor for MCP tools."""

    def __init__(self, tool_name: str, client: MCPClient):
        self.tool_name = tool_name
        self.client = client

    async def call_tool(self, action: SchemaInstance) -> SchemaInstance:
        async with self.client:
            assert self.client.is_connected(), "MCP client is not connected."
            try:
                logger.debug(
                    f"Calling MCP tool {self.tool_name} with args: {action.data}"
                )
                result: mcp.types.CallToolResult = await self.client.call_tool_mcp(
                    name=self.tool_name, arguments=action.data
                )
                return MCPToolObservation.from_call_tool_result(
                    tool_name=self.tool_name, result=result
                )
            except Exception as e:
                error_msg = f"Error calling MCP tool {self.tool_name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                from openhands.sdk.mcp.definition import make_mcp_observation_schema

                return SchemaInstance(
                    schema=make_mcp_observation_schema(),
                    data={
                        "content": [TextContent(text=error_msg)],
                        "is_error": True,
                        "tool_name": self.tool_name,
                    },
                )

    def __call__(self, action: SchemaInstance) -> SchemaInstance:
        """Execute an MCP tool call."""
        return self.client.call_async_from_sync(
            self.call_tool, action=action, timeout=300
        )


class MCPTool(Tool):
    """MCP Tool that wraps an MCP client and provides tool functionality."""

    mcp_tool: mcp.types.Tool = Field(description="The MCP tool definition.")

    @computed_field(return_type=str)
    @property
    def kind(self) -> str:
        """Return the fully qualified class name."""
        return f"{self.__class__.__module__}.{self.__class__.__name__}"

    @classmethod
    def create(
        cls,
        mcp_tool: mcp.types.Tool,
        mcp_client: MCPClient,
    ) -> "MCPTool":
        try:
            annotations = (
                ToolAnnotations.model_validate(
                    mcp_tool.annotations.model_dump(exclude_none=True)
                )
                if mcp_tool.annotations
                else None
            )

            # Convert MCP input schema to our Schema format
            input_schema = mcp_schema_to_schema(
                f"openhands.sdk.mcp.{mcp_tool.name}.input",
                mcp_tool.inputSchema or {},
            )

            from openhands.sdk.mcp.definition import make_mcp_observation_schema

            output_schema = make_mcp_observation_schema()

            return cls(
                name=mcp_tool.name,
                description=mcp_tool.description or "No description provided",
                input_schema=input_schema,
                output_schema=output_schema,
                annotations=annotations,
                meta=mcp_tool.meta,
                executor=MCPToolExecutor(tool_name=mcp_tool.name, client=mcp_client),
                # pass-through fields (enabled by **extra in Tool.create)
                mcp_tool=mcp_tool,
            )
        except ValidationError as e:
            logger.error(
                f"Validation error creating MCPTool for {mcp_tool.name}: "
                f"{e.json(indent=2)}",
                exc_info=True,
            )
            raise e
