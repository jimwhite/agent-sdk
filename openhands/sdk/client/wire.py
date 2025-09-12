from typing import Any

from pydantic import BaseModel


class WireCodec:
    """Minimal (de)serializer for Pydantic models."""

    @staticmethod
    def to_wire(x: Any) -> Any:
        if isinstance(x, BaseModel):
            return {
                "__model__": x.__class__.__name__,
                "data": x.model_dump(mode="json"),
            }
        if isinstance(x, (list, tuple)):
            return [WireCodec.to_wire(i) for i in x]
        if isinstance(x, dict):
            return {k: WireCodec.to_wire(v) for k, v in x.items()}
        return x

    @staticmethod
    def from_wire(x: Any, registry: dict[str, type[BaseModel]]) -> Any:
        if isinstance(x, dict) and "__model__" in x:
            name = x["__model__"]
            cls = registry.get(name)
            if cls is not None and issubclass(cls, BaseModel):
                return cls.model_validate(x["data"])
        if isinstance(x, list):
            return [WireCodec.from_wire(i, registry) for i in x]
        if isinstance(x, dict):
            return {k: WireCodec.from_wire(v, registry) for k, v in x.items()}
        return x
