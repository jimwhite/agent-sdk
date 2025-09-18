from __future__ import annotations

import re
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    create_model,
    field_validator,
    model_validator,
)
from rich.text import Text

from openhands.sdk.tool.schema.types import (
    BoolType,
    DictType,
    FloatType,
    IntType,
    ListType,
    NoneType,
    SchemaFieldType,
    StringType,
)


class SchemaField(BaseModel):
    """A single field of the Schema."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(..., description="Name of the field")
    description: str = Field(
        description="Description of the field. Will be shown to the "
        "model as part of the tool definition.",
    )
    type: SchemaFieldType = Field(
        ...,
        description="Type of the field, either a SchemaFieldType",
    )
    required: bool = Field(
        default=False,
        description="Whether the field is required (default: True). "
        "If False, the field is optional.",
    )
    default: Any | None = Field(
        default=None,
        description="Default value for the field if not provided. "
        "If required is True and default is None, the field must be provided.",
    )
    enum: list[Any] | None = Field(
        default=None,
        description="Optional list of allowed values for the field",
    )

    @model_validator(mode="after")
    def check_default(self) -> SchemaField:
        if self.required and self.default is not None:
            raise ValueError("Field cannot be required and have a default value")
        return self

    @classmethod
    def create(
        cls,
        *,
        name: str,
        description: str,
        type: type[Any] | SchemaFieldType,
        required: bool = False,
        default: Any | None = None,
        enum: list[Any] | None = None,
    ) -> "SchemaField":
        return cls(
            name=name,
            description=description,
            type=type
            if isinstance(type, SchemaFieldType)
            else SchemaFieldType.from_type(type),
            required=required,
            default=default,
            enum=enum,
        )


class Schema(BaseModel):
    """Self-describing schema that travels with payloads.

    This is used to define the input/output schema for tools.
    1. It can be converted to MCP/OpenAI-style JSON schema for model tool use.
    2. It can be converted to a Pydantic model for validation and parsing.
    3. It is self-contained and serializable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str = Field(
        description="Human-readable name for the schema, "
        "e.g. openhands.tools.str_replace_editor.action; "
        "should have package-like format (dot-separated, no spaces), "
        "and ends with either .action or .observation",
    )
    fields: list[SchemaField] = Field(
        default_factory=list,
        description="List of fields in the schema",
    )

    @field_validator("name")
    def must_be_package_and_end_correctly(cls, v: str) -> str:
        # Pattern for package-like identifiers:
        #   - segments separated by dots
        #   - each segment starts with a letter/underscore and
        # followed by letters/digits/underscores
        PACKAGE_PATTERN = re.compile(
            r"^(?:[a-zA-Z_][a-zA-Z0-9_]*)(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*$"
        )
        if not PACKAGE_PATTERN.match(v):
            raise ValueError("Value must be a valid dotted package path")
        if not (v.endswith(".action") or v.endswith(".observation")):
            raise ValueError("Value must end with '.action' or '.observation'")
        return v

    def to_mcp_schema(self) -> dict[str, Any]:
        props: dict[str, Any] = {}
        required: list[str] = []
        for f in self.fields:
            node = self._to_mcp_node(f.type)
            if f.description:
                node["description"] = f.description
            if f.enum is not None:
                node["enum"] = f.enum
            props[f.name] = node
            if f.required and f.default is None:
                required.append(f.name)
        out: dict[str, Any] = {"type": "object", "properties": props}
        if required:
            out["required"] = required
        return out

    @staticmethod
    def _to_mcp_node(t: SchemaFieldType) -> dict[str, Any]:
        from .types import CustomType, UnionType

        p = t.payload
        if isinstance(p, StringType):
            return {"type": "string"}
        elif isinstance(p, IntType):
            return {"type": "integer"}
        elif isinstance(p, FloatType):
            return {"type": "number"}
        elif isinstance(p, BoolType):
            return {"type": "boolean"}
        elif isinstance(p, NoneType):
            return {"type": "null"}
        elif isinstance(p, ListType):
            return {"type": "array", "items": Schema._to_mcp_node(p.item_type)}
        elif isinstance(p, DictType):
            return {"type": "object"}
        elif isinstance(p, UnionType):
            # For Union types, use anyOf in JSON Schema
            return {
                "anyOf": [Schema._to_mcp_node(union_type) for union_type in p.types]
            }
        elif isinstance(p, CustomType):
            # For custom Pydantic models, represent as object for now
            # In a full implementation, we'd introspect the model fields
            return {"type": "object", "description": f"Custom type: {p.class_name}"}
        return {"type": "string"}

    def build_args_model(self) -> type[BaseModel]:
        """Always build a fresh Pydantic model from this schema."""
        fields: dict[str, tuple[Any, Any]] = {}
        required = {f.name for f in self.fields if f.required and f.default is None}

        from typing import Literal as _Literal

        for f in self.fields:
            ann = f.type.to_type()
            if f.enum:
                ann = _Literal[tuple(f.enum)]  # type: ignore[index]
            if f.name not in required and f.default is None:
                ann = ann | type(None)
            default = ... if f.name in required else f.default
            fields[f.name] = (ann, Field(default=default, description=f.description))

        return create_model(f"{self.name.replace('.', '_')}_Args", **fields)  # type: ignore[arg-type]


class SchemaInstance(BaseModel):
    """Schema definition + actual data travel together.

    Data is typically a dict returned by LLM or tool executor.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, arbitrary_types_allowed=True)
    name: str = Field(..., description="Name of this schema instance")
    definition: Schema = Field(..., description="The schema definition")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="The actual data conforming to the schema",
    )

    @field_validator("name")
    def must_be_camel_case(cls, v: str) -> str:
        CAMEL_CASE_PATTERN = re.compile(r"^[a-z]+(?:[A-Z][a-z0-9]*)*$")
        if not CAMEL_CASE_PATTERN.match(v):
            raise ValueError("Value must be camelCase")
        return v

    def validate_data(self) -> BaseModel:
        Model = self.definition.build_args_model()
        return Model.model_validate(self.data)

    @property
    def agent_observation(self) -> list:
        """Default agent observation - returns data as TextContent."""
        # Convert data to a simple string representation
        import json

        from openhands.sdk.llm.message import TextContent

        data_str = json.dumps(self.data, indent=2)
        return [TextContent(text=data_str)]

    @property
    def visualize(self) -> Text:
        """Return Rich Text representation of this schema instance."""
        from openhands.sdk.utils.visualize import display_dict

        content = Text()
        content.append(f"{self.name}:\n", style="bold")
        content.append(display_dict(self.data))
        return content
