"""
Schema registry system for dynamic action and observation schemas.

This module provides a replacement for DiscriminatedUnionMixin that uses
vanilla Pydantic with a registry-based approach for dynamic schema management.
"""

from __future__ import annotations

import importlib
from typing import Any, TypeVar, get_args, get_origin

from pydantic import BaseModel, TypeAdapter, create_model
from pydantic_core import PydanticUndefined


T = TypeVar("T", bound=BaseModel)


def kind_of(t: type) -> str:
    """Get the kind string for a given class."""
    return f"{t.__module__}.{t.__qualname__}"


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


class SchemaRegistry:
    """Registry for managing dynamic schemas without inheritance requirements."""

    def __init__(self):
        self._schemas: dict[str, type[BaseModel]] = {}
        self._specs: dict[str, dict[str, Any]] = {}

    def register_schema(self, schema_class: type[BaseModel]) -> None:
        """Register a schema class in the registry."""
        kind = kind_of(schema_class)
        self._schemas[kind] = schema_class

        # Store the spec for potential reconstruction
        spec = self._create_spec(schema_class)
        self._specs[kind] = spec

    def get_schema(self, kind: str) -> type[BaseModel] | None:
        """Get a registered schema by kind string."""
        # First try direct lookup
        if kind in self._schemas:
            return self._schemas[kind]

        # Try to import and register the class
        schema_class = self._resolve_kind_via_import(kind)
        if schema_class:
            self.register_schema(schema_class)
            return schema_class

        return None

    def create_from_spec(self, spec: dict[str, Any], data: dict[str, Any]) -> BaseModel:
        """Create a model instance from a spec and data."""
        base_cls = BaseModel

        # Try to resolve the base class
        base_name = spec.get("base")
        if isinstance(base_name, str):
            base_cls = self._resolve_kind_via_import(base_name) or base_cls

        # Build field definitions
        field_defs: dict[str, tuple[Any, Any]] = {}
        for name, meta in spec.get("fields", {}).items():
            tname = meta.get("type", "Any")
            # Map common type names
            typemap: dict[str, Any] = {
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "list": list,
                "dict": dict,
                "Any": Any,
            }
            ann = typemap.get(tname.split("[", 1)[0], Any)
            field_defs[name] = (
                ann,
                ... if meta.get("required", False) else meta.get("default", None),
            )

        # Create temporary model
        TempModel = create_model(
            spec.get("title", "DynamicModel"),
            __base__=base_cls,
            **field_defs,  # type: ignore[arg-type]
        )

        return TempModel.model_validate(data)

    def _create_spec(self, schema_class: type[BaseModel]) -> dict[str, Any]:
        """Create a spec dictionary from a schema class."""
        fields: dict[str, dict[str, Any]] = {}

        for fname, f in schema_class.model_fields.items():
            info: dict[str, Any] = {"type": _type_to_str(f.annotation)}
            if f.is_required():
                info["required"] = True
            else:
                info["required"] = False

                # Only include a concrete, JSON-safe default
                default = getattr(f, "default", PydanticUndefined)
                default_factory = getattr(f, "default_factory", None)
                if default is not PydanticUndefined and default_factory is None:
                    jsonable = TypeAdapter(Any).dump_python(default, mode="json")
                    if jsonable is not None:
                        info["default"] = jsonable

            fields[fname] = info

        return {
            "title": kind_of(schema_class),
            "base": kind_of(schema_class),
            "fields": fields,
        }

    def _resolve_kind_via_import(self, kind: str) -> type[BaseModel] | None:
        """Try to import and resolve a kind string to a class."""
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

            if isinstance(attr, type) and issubclass(attr, BaseModel):
                return attr

        return None

    def register_dynamic_schema(self, schema_class: type[BaseModel]) -> None:
        """Register a dynamically created schema class.

        This is useful for classes created via create_model() that can't be imported.
        """
        kind = kind_of(schema_class)
        self._schemas[kind] = schema_class


# Global registry instances
action_registry = SchemaRegistry()
observation_registry = SchemaRegistry()
tool_registry = SchemaRegistry()


def register_action_schema(schema_class: type[BaseModel]) -> None:
    """Register an action schema."""
    action_registry.register_schema(schema_class)


def register_observation_schema(schema_class: type[BaseModel]) -> None:
    """Register an observation schema."""
    observation_registry.register_schema(schema_class)


def register_tool_schema(schema_class: type[BaseModel]) -> None:
    """Register a tool schema."""
    tool_registry.register_schema(schema_class)


def register_dynamic_action_schema(schema_class: type[BaseModel]) -> None:
    """Register a dynamically created action schema."""
    action_registry.register_dynamic_schema(schema_class)


def register_dynamic_observation_schema(schema_class: type[BaseModel]) -> None:
    """Register a dynamically created observation schema."""
    observation_registry.register_dynamic_schema(schema_class)


def validate_action(data: dict[str, Any]) -> BaseModel:
    """Validate action data using the registry."""
    return _validate_with_registry(data, action_registry)


def validate_observation(data: dict[str, Any]) -> BaseModel:
    """Validate observation data using the registry."""
    return _validate_with_registry(data, observation_registry)


def validate_tool(data: dict[str, Any]) -> BaseModel:
    """Validate tool data using the registry."""
    return _validate_with_registry(data, tool_registry)


def _validate_with_registry(
    data: dict[str, Any], registry: SchemaRegistry
) -> BaseModel:
    """Validate data using a specific registry."""
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    kind = data.get("kind")
    spec = data.get("_du_spec")

    # Try to resolve by kind first
    if isinstance(kind, str):
        schema_class = registry.get_schema(kind)
        if schema_class:
            # Remove control fields before validation
            clean_data = {
                k: v for k, v in data.items() if k not in ("kind", "_du_spec")
            }
            return schema_class.model_validate(clean_data)

    # Fallback to spec reconstruction
    if isinstance(spec, dict):
        clean_data = {k: v for k, v in data.items() if k not in ("kind", "_du_spec")}
        return registry.create_from_spec(spec, clean_data)

    # Final fallback - use appropriate base class
    from openhands.sdk.tool.schema import ActionBase, ObservationBase
    from openhands.sdk.tool.tool import Tool

    clean_data = {k: v for k, v in data.items() if k not in ("kind", "_du_spec")}

    # Use appropriate base class based on registry type
    if registry is action_registry:
        return ActionBase.model_validate(clean_data)
    elif registry is observation_registry:
        return ObservationBase.model_validate(clean_data)
    elif registry is tool_registry:
        return Tool.model_validate(clean_data)
    else:
        # Generic fallback - create a dynamic model
        from typing import Any

        from pydantic import create_model

        # Create field definitions for create_model
        field_definitions = {}
        for k, v in clean_data.items():
            field_definitions[k] = (Any, v)

        DynamicModel = create_model("DynamicModel", **field_definitions)
        return DynamicModel.model_validate(clean_data)
