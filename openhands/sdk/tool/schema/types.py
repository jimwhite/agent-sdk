# openhands/sdk/SchemaField/schema.py
from __future__ import annotations

from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field


# ---------- Simple type universe (self-serializing) ----------


class StringType(BaseModel):
    type_name: Literal["string"] = "string"

    def to_type(self) -> type:
        return str


class IntType(BaseModel):
    type_name: Literal["int"] = "int"

    def to_type(self) -> type:
        return int


class FloatType(BaseModel):
    type_name: Literal["float"] = "float"

    def to_type(self) -> type:
        return float


class BoolType(BaseModel):
    type_name: Literal["bool"] = "bool"

    def to_type(self) -> type:
        return bool


class NoneType(BaseModel):
    type_name: Literal["none"] = "none"

    def to_type(self) -> type:
        return type(None)


class ListType(BaseModel):
    type_name: Literal["list"] = "list"
    item_type: "SchemaFieldType"

    def to_type(self) -> Any:
        return list[self.item_type.to_type()]


class DictType(BaseModel):
    type_name: Literal["dict"] = "dict"
    key_type: "SchemaFieldType"
    value_type: "SchemaFieldType"

    def to_type(self) -> Any:
        return dict[self.key_type.to_type(), self.value_type.to_type()]


SchemaFieldTypePayload = (
    StringType | IntType | FloatType | BoolType | NoneType | ListType | DictType
)


class SchemaFieldType(BaseModel):
    """Serializable representation of a Python-ish type.

    This is used to represent the types of fields in Schema
    for action/observation (tool input/output schema).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    payload: SchemaFieldTypePayload = Field(discriminator="type_name")

    @staticmethod
    def from_type(tp: Any) -> "SchemaFieldType":
        if tp is str:
            return SchemaFieldType(payload=StringType())
        if tp is int:
            return SchemaFieldType(payload=IntType())
        if tp is float:
            return SchemaFieldType(payload=FloatType())
        if tp is bool:
            return SchemaFieldType(payload=BoolType())
        if tp is type(None):
            return SchemaFieldType(payload=NoneType())

        origin = get_origin(tp)
        args = get_args(tp)

        if origin is list and len(args) == 1:
            return SchemaFieldType(
                payload=ListType(item_type=SchemaFieldType.from_type(args[0]))
            )
        if origin is dict and len(args) == 2:
            return SchemaFieldType(
                payload=DictType(
                    key_type=SchemaFieldType.from_type(args[0]),
                    value_type=SchemaFieldType.from_type(args[1]),
                )
            )
        raise ValueError(f"Unsupported type: {tp!r}")

    def to_type(self) -> Any:
        return self.payload.to_type()
