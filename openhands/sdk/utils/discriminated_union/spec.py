import importlib
from typing import Any, get_args, get_origin

from pydantic import BaseModel

from openhands.sdk.utils.discriminated_union.simple_type import SimpleType


def kind_of(t: type) -> str:
    """Get the kind string for a given class."""
    return f"{t.__module__}.{t.__qualname__}"


def _resolve_kind_via_import(cls, kind: str):
    parts = kind.split(".")
    for i in range(len(parts) - 1, 0, -1):
        try:
            module = importlib.import_module(".".join(parts[:i]))
        except ModuleNotFoundError:
            continue
        attr = module
        for name in parts[i:]:
            try:
                attr = getattr(attr, name)
            except AttributeError:
                attr = None
                break
        if isinstance(attr, type) and issubclass(attr, cls):
            return attr
    return None


def _type_to_str(tp: Any) -> str:
    """Best-effort readable type name (for fallback only)."""
    try:
        origin = get_origin(tp)
        if origin:
            args = ", ".join(_type_to_str(a) for a in get_args(tp))
            return f"{origin.__name__}[{args}]"
        if isinstance(tp, type):
            return tp.__name__
        return str(tp)
    except Exception:
        return "Any"


class SpecField(BaseModel):
    name: str
    type: SimpleType
    required: bool
    default: Any | None = None


class Spec(BaseModel):
    name: str
    base: str
    fields: list[SpecField] | None = None
