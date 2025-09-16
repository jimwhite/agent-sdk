from typing import Any, Generic, TypeVar

from litellm import ChatCompletionToolParam, ChatCompletionToolParamFunctionChunk
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

from openhands.sdk.tool.schema import ActionBase, ObservationBase


ActionT = TypeVar("ActionT", bound=ActionBase)
ObservationT = TypeVar("ObservationT", bound=ObservationBase)


class ToolAnnotations(BaseModel):
    """Annotations to provide hints about the tool's behavior.

    Based on Model Context Protocol (MCP) spec:
    https://github.com/modelcontextprotocol/modelcontextprotocol/blob/caf3424488b10b4a7b1f8cb634244a450a1f4400/schema/2025-06-18/schema.ts#L838
    """

    model_config = ConfigDict(
        frozen=True,
        # We need to define the title here to avoid conflict with MCP's ToolAnnotations
        # when both are included in the same JSON schema for openapi.json
        title="openhands.sdk.tool.tool.ToolAnnotations",
    )

    title: str | None = Field(
        default=None, description="A human-readable title for the tool."
    )
    readOnlyHint: bool = Field(
        default=False,
        description="If true, the tool does not modify its environment. Default: false",
    )
    destructiveHint: bool = Field(
        default=True,
        description="If true, the tool may perform destructive updates to its environment. If false, the tool performs only additive updates. (This property is meaningful only when `readOnlyHint == false`) Default: true",  # noqa: E501
    )
    idempotentHint: bool = Field(
        default=False,
        description="If true, calling the tool repeatedly with the same arguments will have no additional effect on the its environment. (This property is meaningful only when `readOnlyHint == false`) Default: false",  # noqa: E501
    )
    openWorldHint: bool = Field(
        default=True,
        description="If true, this tool may interact with an 'open world' of external entities. If false, the tool's domain of interaction is closed. For example, the world of a web search tool is open, whereas that of a memory tool is not. Default: true",  # noqa: E501
    )


class ToolExecutor(Generic[ActionT, ObservationT]):
    """Executor function type for a Tool."""

    def __call__(self, action: ActionT) -> ObservationT:
        raise NotImplementedError

    def close(self) -> None:
        """Close the executor and clean up resources.

        Default implementation does nothing. Subclasses should override
        this method to perform cleanup (e.g., closing connections,
        terminating processes, etc.).
        """
        pass


class Tool(BaseModel, Generic[ActionT, ObservationT]):
    """Tool that wraps an executor function with input/output validation and schema.

    - Normalize input/output schemas (class or dict) into both model+schema.
    - Validate inputs before execute.
    - Coerce outputs only if an output model is defined; else return vanilla JSON.
    - Export MCP tool description.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="allow")

    name: str
    description: str
    # Persist schema; reconstruct types at runtime. Exclude types from dumps.
    action_type: type[ActionBase] | None = Field(default=None, repr=False, exclude=True)
    observation_type: type[ObservationBase] | None = Field(
        default=None, repr=False, exclude=True
    )
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None

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

    @model_validator(mode="after")
    def _sync_types_and_schemas(self):
        # Populate input/output schemas from types if missing
        if self.action_type is not None and self.input_schema is None:
            object.__setattr__(self, "input_schema", self.action_type.to_mcp_schema())
        if self.observation_type is not None and self.output_schema is None:
            object.__setattr__(
                self, "output_schema", self.observation_type.to_mcp_schema()
            )

        # If types are missing but schemas provided, reconstruct runtime models
        if self.action_type is None and self.input_schema is not None:
            model_name = (
                self.annotations.title
                if self.annotations and self.annotations.title
                else self.name
            ) + "Action"
            object.__setattr__(
                self,
                "action_type",
                ActionBase.from_mcp_schema(model_name, self.input_schema),
            )
        if self.observation_type is None:
            if self.output_schema is not None:
                model_name = self.name + "Observation"
                object.__setattr__(
                    self,
                    "observation_type",
                    ObservationBase.from_mcp_schema(model_name, self.output_schema),
                )
            # MCP fallback: if we detect MCP metadata and no output schema was provided,
            # default to MCPToolObservation for compatibility
            elif getattr(self, "mcp_tool", None) is not None:
                from openhands.sdk.mcp.definition import MCPToolObservation

                object.__setattr__(self, "observation_type", MCPToolObservation)
        return self

    @computed_field(return_type=str, alias="title")
    @property
    def title(self) -> str:
        if self.annotations and self.annotations.title:
            return self.annotations.title
        return self.name

    def set_executor(self, executor: ToolExecutor) -> "Tool":
        """Create a new Tool instance with the given executor."""
        return self.model_copy(update={"executor": executor})

    def call(self, action: ActionT) -> ObservationBase:
        """Validate input, execute, and coerce output.

        We always return some ObservationBase subclass, but not always the
        generic ObservationT.
        """
        if self.executor is None:
            raise NotImplementedError(f"Tool '{self.name}' has no executor")

        # Execute
        result = self.executor(action)

        # Coerce output only if we declared a model; else wrap in base ObservationBase
        if self.observation_type:
            if isinstance(result, self.observation_type):
                return result
            return self.observation_type.model_validate(result)
        else:
            # When no output schema is defined, wrap the result in ObservationBase
            if isinstance(result, ObservationBase):
                return result
            elif isinstance(result, BaseModel):
                return ObservationBase.model_validate(result.model_dump())
            elif isinstance(result, dict):
                return ObservationBase.model_validate(result)
            raise TypeError(
                "Output must be dict or BaseModel when no output schema is defined"
            )

    def to_mcp_tool(self) -> dict[str, Any]:
        out = {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
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
                parameters=self.input_schema or {},
            ),
        )


ToolType = Tool[ActionT, ObservationT]
