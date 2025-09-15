from __future__ import annotations

from typing import Annotated, Literal, Union, get_args, get_origin

from pydantic import BaseModel, Field


class StringType(BaseModel):
    _type: Literal["string"] = "string"

    def to_type(self) -> type:
        return str


class IntType(BaseModel):
    _type: Literal["int"] = "int"

    def to_type(self) -> type:
        return int


class FloatType(BaseModel):
    _type: Literal["float"] = "float"

    def to_type(self) -> type:
        return float


class BoolType(BaseModel):
    _type: Literal["bool"] = "bool"

    def to_type(self) -> type:
        return bool


class NoneType(BaseModel):
    _type: Literal["none"] = "none"

    def to_type(self) -> type:
        return type(None)


class ListType(BaseModel):
    _type: Literal["list"] = "list"
    item_type: SimpleTypePayload

    def to_type(self) -> type:
        return list[self.item_type.to_type()]


class DictType(BaseModel):
    _type: Literal["dict"] = "dict"
    key_type: SimpleTypePayload
    value_type: SimpleTypePayload

    def to_type(self) -> type:
        return dict[self.key_type.to_type(), self.value_type.to_type()]


SimpleTypePayload = Annotated[
    Union[
        StringType,
        IntType,
        FloatType,
        BoolType,
        NoneType,
        ListType,
        DictType,
    ],
    Field(discriminator="type"),
]


class SimpleType(BaseModel):
    payload: SimpleTypePayload

    @staticmethod
    def from_type(type_obj: type) -> SimpleType:
        """Create a SimpleType from a Python type object.

        Args:
            type_obj: The Python type to convert (str, int, float, bool, type(None),
            list, dict, or parameterized versions)

        Returns:
            SimpleType instance representing the type.

        Raises:
            ValueError: If the type is not supported.
        """
        # Handle basic types
        if type_obj is str:
            return SimpleType(payload=StringType())
        elif type_obj is int:
            return SimpleType(payload=IntType())
        elif type_obj is float:
            return SimpleType(payload=FloatType())
        elif type_obj is bool:
            return SimpleType(payload=BoolType())
        elif type_obj is type(None):
            return SimpleType(payload=NoneType())

        # Handle parameterized types
        origin = get_origin(type_obj)
        args = get_args(type_obj)

        if origin is list:
            if len(args) == 1:
                element_type = SimpleType.from_type(args[0])
                return SimpleType(payload=ListType(item_type=element_type.payload))

        elif origin is dict:
            if len(args) == 2:
                key_type = SimpleType.from_type(args[0])
                value_type = SimpleType.from_type(args[1])
                return SimpleType(
                    payload=DictType(
                        key_type=key_type.payload, value_type=value_type.payload
                    )
                )

        # Unsupported type
        type_name = getattr(type_obj, "__name__", str(type_obj))
        raise ValueError(
            f"Unsupported type: {type_name}. "
            "Supported types are: str, int, float, bool, type(None), list, and dict."
        )

    def to_type(self) -> type:
        """Convert back to the original Python type object."""
        return self.payload.to_type()
