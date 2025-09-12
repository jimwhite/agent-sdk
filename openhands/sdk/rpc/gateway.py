from typing import Any, Optional, Type, TypeVar

from pydantic import BaseModel

from .handle import RemoteHandle
from .transport import HTTPTransport
from .wire import WireCodec


T = TypeVar("T")


class RuntimeGateway:
    """
    Entry point. Keeps a route map and a model registry, and exposes:
      - bind(cls): returns a remote class factory
      - routes: dict[(class, method)] -> (HTTP_METHOD, path)
      - sync_routes(): fill routes from /rpc/schema
    """

    def __init__(
        self, base_url: str, api_key: Optional[str] = None, timeout: float = 30.0
    ):
        self.transport = HTTPTransport(base_url, api_key=api_key, timeout=timeout)
        self.model_registry: dict[str, type[BaseModel]] = {}
        self.routes: dict[tuple[str, str], tuple[str, str]] = {}

    # ---- public --------------------------------------------------------------

    def bind(self, cls: Type[T]) -> Type[T]:
        class_name = cls.__name__

        def _gateway_call(_class: str, method: str, payload: dict[str, Any]) -> Any:
            # Extract instance ID from payload
            instance_id = None
            inst = payload.get("instance")
            if isinstance(inst, dict):
                instance_id = inst.get("id") or inst.get("conversation_id")

            http_method, path = self._resolve_route(_class, method, instance_id)

            def _to_plain(obj: Any) -> Any:
                if isinstance(obj, BaseModel):
                    return obj.model_dump()
                if isinstance(obj, dict):
                    # unwrap WireCodec model envelope if present
                    if (
                        "__model__" in obj
                        and "data" in obj
                        and isinstance(obj["data"], dict)
                    ):
                        return _to_plain(obj["data"])
                    return {k: _to_plain(v) for k, v in obj.items()}
                if isinstance(obj, (list, tuple)):
                    return [_to_plain(i) for i in obj]
                return obj

            if http_method == "POST":
                body = _to_plain(payload.get("kwargs", {}))
                return self.transport.request(http_method, path, body)
            elif http_method == "GET":
                # For GET requests, send kwargs as query parameters
                params = _to_plain(payload.get("kwargs", {}))
                return self.transport.request(http_method, path, None, params=params)
            else:
                return self.transport.request(http_method, path, None)

        _gateway_call.registry = self.model_registry  # type: ignore[attr-defined]

        gateway = self  # Capture reference to the gateway

        class _Remote:
            __name__ = class_name

            def __init__(self, **kwargs):
                if class_name == "Conversation":
                    # Use the constructor endpoint for Conversation
                    def _to_plain(obj: Any) -> Any:
                        if isinstance(obj, BaseModel):
                            return obj.model_dump(mode="json")
                        if isinstance(obj, dict):
                            return {k: _to_plain(v) for k, v in obj.items()}
                        if isinstance(obj, (list, tuple)):
                            return [_to_plain(i) for i in obj]
                        return obj

                    body = _to_plain(kwargs)
                    result = gateway.transport.request("POST", "/conversation", body)
                    conversation_id = result["id"]

                    # Create state with the returned ID
                    state = {"id": conversation_id, "conversation_id": conversation_id}
                else:
                    # For other classes, use the old approach
                    state = WireCodec.to_wire(kwargs)

                self._handle = RemoteHandle(
                    class_name=class_name, state=state, gateway_call=_gateway_call
                )

            def __getattr__(self, name: str):
                return getattr(self._handle, name)

            def model_dump(self) -> dict[str, Any]:
                return self._handle.model_dump()

        return _Remote  # type: ignore[return-value]

    def register_models(self, models: dict[str, type[BaseModel]]) -> None:
        self.model_registry.update(models)

    def health_check(self) -> dict[str, Any]:
        return self.transport.request("GET", "/alive")

    def sync_routes(self) -> None:
        schema = self.transport.request("GET", "/api/schema")
        self.routes.clear()
        for r in schema:
            self.routes[(r["class"], r["method"])] = (r["http"], r["path"])

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> "RuntimeGateway":
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    # ---- internals -----------------------------------------------------------

    def _resolve_route(
        self, class_name: str, method_name: str, instance_id: str | None = None
    ) -> tuple[str, str]:
        """Resolve a (class, method) pair to (http_method, path)."""
        key = (class_name, method_name)
        if key not in self.routes:
            raise ValueError(f"Route not found: {class_name}.{method_name}")

        http_method, path = self.routes[key]

        # Replace {id} placeholder with actual instance_id
        if "{id}" in path and instance_id:
            path = path.replace("{id}", instance_id)

        return http_method, path
