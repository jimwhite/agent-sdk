# endpoints.py
from typing import Callable, Optional

from pydantic import BaseModel


class RouteSpec(BaseModel):
    class_name: str
    method_name: str
    http: str = "POST"
    path: str
    instance_scoped: bool = True
    request_in: str = "body"  # "body" or "query"
    auth_required: bool = True


class APIRegistry:
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
            cls._api_service_name = name or cls.__name__
            self._impls[cls._api_service_name] = cls
            return cls

        return wrap

    def method(
        self,
        path: str,
        http: str = "POST",
        instance_scoped: bool = True,
        request_in: str = "body",
        auth_required: bool = True,
    ):
        def deco(fn: Callable) -> Callable:
            setattr(
                fn,
                "_api_route",
                {
                    "path": path,
                    "http": http,
                    "instance_scoped": instance_scoped,
                    "request_in": request_in,
                    "auth_required": auth_required,
                },
            )
            return fn

        return deco

    def collect(self) -> None:
        self._routes.clear()
        for cls_name, cls in self._impls.items():
            for attr in dir(cls):
                if attr.startswith("_"):
                    continue
                fn = getattr(cls, attr)
                meta = getattr(fn, "_api_route", None)
                if not meta:
                    continue
                self._routes[(cls_name, attr)] = RouteSpec(
                    class_name=cls_name,
                    method_name=attr,
                    http=meta["http"],
                    path=meta["path"],
                    instance_scoped=meta.get("instance_scoped", True),
                    request_in=meta.get("request_in", "body"),
                    auth_required=meta.get("auth_required", True),
                )

    def get_impl_class(self, class_name: str) -> type:
        return self._impls[class_name]


api = APIRegistry()
