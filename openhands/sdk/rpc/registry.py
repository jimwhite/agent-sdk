# registry.py
from typing import Callable, Optional

from pydantic import BaseModel


class RouteSpec(BaseModel):
    class_name: str
    method_name: str
    http: str = "POST"
    path: str


class RouteRegistry:
    """
    Pure metadata container for services and method routes.
    Lives in SDK so implementations can decorate without pulling server deps.
    """

    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], RouteSpec] = {}
        self._impls: dict[str, type] = {}

    @property
    def routes(self) -> dict[tuple[str, str], RouteSpec]:
        return self._routes

    def service(self, name: Optional[str] = None):
        def wrap(cls: type) -> type:
            cls._rpc_service_name = name or cls.__name__
            self._impls[cls._rpc_service_name] = cls
            return cls

        return wrap

    def method(self, path: str, http: str = "POST"):
        def deco(fn: Callable) -> Callable:
            setattr(fn, "_rpc_route", {"path": path, "http": http})
            return fn

        return deco

    def collect(self) -> None:
        self._routes.clear()
        for cls_name, cls in self._impls.items():
            for attr in dir(cls):
                if attr.startswith("_"):
                    continue
                fn = getattr(cls, attr)
                meta = getattr(fn, "_rpc_route", None)
                if not meta:
                    continue
                self._routes[(cls_name, attr)] = RouteSpec(
                    class_name=cls_name,
                    method_name=attr,
                    http=meta["http"],
                    path=meta["path"],
                )

    def get_impl_class(self, class_name: str) -> type:
        return self._impls[class_name]


rpc = RouteRegistry()
