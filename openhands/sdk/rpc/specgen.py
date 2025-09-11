import inspect
from typing import Annotated, Any, get_type_hints

from pydantic import BaseModel, create_model


class ServerOnly:
    """Marker used in Annotated[..., ServerOnly] to exclude from wire spec."""

    pass


def _is_server_only(ann: Any) -> bool:
    # Works for typing.Annotated[T, ...]
    origin = getattr(ann, "__origin__", None)
    metadata = getattr(ann, "__metadata__", ())
    return bool(
        origin is Annotated
        and any(isinstance(m, ServerOnly) or m is ServerOnly for m in metadata)
    )


def make_spec_from_init(
    cls: type,
    *,
    exclude: set[str] = set(),
    overrides: dict[str, Any] | None = None,
    name: str | None = None,
) -> type[BaseModel]:
    """
    Build a Pydantic model from cls.__init__ params, minus `self` and excluded.
    `overrides` lets you force a type (e.g., Agent -> AgentSpec).
    - Skips parameters annotated as Annotated[..., ServerOnly]
    """
    sig = inspect.signature(cls.__init__)
    hints = get_type_hints(cls.__init__)
    overrides = overrides or {}
    fields: dict[str, tuple[Any, Any]] = {}

    for pname, p in sig.parameters.items():
        if pname in ("self",):
            continue
        if pname in exclude:
            continue

        ann = overrides.get(pname, hints.get(pname, Any))
        if _is_server_only(ann):
            continue

        default = p.default if p.default is not inspect._empty else ...
        fields[pname] = (ann, default)

    model_name = name or f"{cls.__name__}Spec"
    return create_model(model_name, **fields)  # type: ignore
