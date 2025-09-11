from typing import Any


_instances: dict[str, Any] = {}


def get_instance(key: str) -> Any | None:
    return _instances.get(key)


def set_instance(key: str, obj: Any) -> None:
    _instances[key] = obj
