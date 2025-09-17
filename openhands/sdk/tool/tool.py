from typing import Any

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

from openhands.sdk.tool.annotations import ToolAnnotations
from openhands.sdk.tool.schema import Schema, SchemaInstance


class ToolExecutor:
    """Executor function type for a Tool."""

    def __call__(self, action: SchemaInstance) -> SchemaInstance:
        raise NotImplementedError

    def close(self) -> None:
        """Close the executor and clean up resources.

        Default implementation does nothing. Subclasses should override
        this method to perform cleanup (e.g., closing connections,
        terminating processes, etc.).
        """
        pass


class Tool(BaseModel):
    """Tool that wraps an executor function with input/output validation and schema.

    - Normalize input/output schemas (class or dict) into both model+schema.
    - Validate inputs before execute.
    - Coerce outputs only if an output model is defined; else return vanilla JSON.
    - Export MCP tool description.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str
    description: str
    input_schema: Schema
    output_schema: Schema | None = None

    annotations: ToolAnnotations | None = None
    meta: dict[str, Any] | None = None

    # runtime-only; always hidden on dumps
    executor: ToolExecutor | None = Field(default=None, repr=False, exclude=True)

    @classmethod
    def create(cls, *args, **kwargs) -> "Tool | list[Tool]":
        """Create a Tool instance OR a list of them. Placeholder for subclasses.

        This can be overridden in subclasses to provide custom initialization logic
            (e.g., typically initializing the executor with parameters).
        """
        raise NotImplementedError("Tool.create() must be implemented in subclasses")

    @computed_field(return_type=str, alias="title")
    @property
    def title(self) -> str:
        if self.annotations and self.annotations.title:
            return self.annotations.title
        return self.name

    def set_executor(self, executor: ToolExecutor) -> "Tool":
        """Create a new Tool instance with the given executor."""
        return self.model_copy(update={"executor": executor})

    def call(self, action: SchemaInstance) -> SchemaInstance:
        """Validate input, execute, and coerce output.

        We always return some ObservationBase subclass, but not always the
        generic ObservationT.
        """
        if self.executor is None:
            raise NotImplementedError(f"Tool '{self.name}' has no executor")

        # Execute
        result = self.executor(action)

        # Validate output
        result.validate_data()
        return result

    def to_mcp_tool(self) -> dict[str, Any]:
        out = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema.to_mcp_schema(),
        }
        if self.annotations:
            out["annotations"] = self.annotations
        if self.meta is not None:
            out["_meta"] = self.meta
        if self.output_schema:
            out["outputSchema"] = self.output_schema
        return out

    def to_openai_tool(self) -> ChatCompletionToolParam:
        """Convert an MCP tool to an OpenAI tool."""
        return ChatCompletionToolParam(
            type="function",
            function=ChatCompletionToolParamFunctionChunk(
                name=self.name,
                description=self.description,
                parameters=self.input_schema.to_mcp_schema(),
            ),
        )
