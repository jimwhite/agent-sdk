# app.py
import inspect
import uuid
from typing import Any, get_type_hints

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, create_model

from openhands.sdk.rpc import rpc
from openhands.sdk.rpc.wire import WireCodec
from openhands.server.state import get_instance, set_instance


# ---- helpers to build request/response models from annotated methods --------


def _make_model_from_params(
    cls_name: str, method_name: str, fn, *, mode: str
) -> type[BaseModel]:
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    fields: dict[str, tuple[Any, Any]] = {}
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        ann = hints.get(name, Any)
        default = param.default if param.default is not inspect._empty else ...
        fields[name] = (ann, default)
    model_name = f"{cls_name}_{method_name}_{'Body' if mode == 'body' else 'Query'}"
    return create_model(model_name, **fields)  # type: ignore


def _response_model(fn) -> Any | None:
    hints = get_type_hints(fn)
    return hints.get("return", None)


# ---- conversation instance bootstrap (expects spec/id) ----------------------


class ConversationCreate(BaseModel):
    """Generic creation DTO with arbitrary 'spec' payload."""

    spec: dict[str, Any] | None = None


def _ensure_instance(
    class_name: str,
    spec: dict[str, Any] | None,
    id_: str | None,
    model_registry: dict[str, type[BaseModel]],
):
    cls = rpc.get_impl_class(class_name)

    if id_:
        inst = get_instance(id_)
        if inst is None:
            raise HTTPException(404, f"{class_name} {id_} not found")
        return id_, inst

    if spec is None:
        raise HTTPException(400, "spec or id is required")

    # allow client to pass 'id' inside spec, else generate one
    conv_id = (spec.get("id") if isinstance(spec, dict) else None) or str(uuid.uuid4())

    inst = get_instance(conv_id)
    if inst is None:
        # Create instance using spec kwargs
        kwargs = (
            WireCodec.from_wire(spec, model_registry) if isinstance(spec, dict) else {}
        )
        inst = cls(**kwargs)
        set_instance(conv_id, inst)

    return conv_id, inst


# ---- app builder ------------------------------------------------------------


def build_app(
    model_registry: dict[str, type[BaseModel]],
    instances: dict[str, Any] | None = None,
) -> FastAPI:
    """
    Build a FastAPI app using routes discovered from decorators on SDK classes.
    """
    app = FastAPI(title="OpenHands Server", version="0.1.0")
    rpc.collect()

    # Discovery for clients
    @app.get("/rpc/schema")
    def schema():
        return [
            {
                "class": s.class_name,
                "method": s.method_name,
                "http": s.http,
                "path": s.path,
            }
            for s in rpc.routes.values()
        ]

    @app.get("/alive")
    def alive():
        return {"ok": True}

    # Generic fallback
    class RPCPayload(BaseModel):
        class_: str
        method: str
        instance: dict[str, Any] = {}
        args: list[Any] = []
        kwargs: dict[str, Any] = {}

    @app.post("/rpc")
    def rpc_generic(payload: RPCPayload):
        cls = rpc.get_impl_class(payload.class_)
        inst = cls(**WireCodec.from_wire(payload.instance, model_registry))
        fn = getattr(inst, payload.method)
        result = fn(
            *WireCodec.from_wire(payload.args, model_registry),
            **WireCodec.from_wire(payload.kwargs, model_registry),
        )
        return {
            "result": WireCodec.to_wire(result),
            "instance": WireCodec.to_wire(
                inst.model_dump() if hasattr(inst, "model_dump") else payload.instance
            ),
        }

    # Explicit decorated endpoints with OpenAPI models
    for spec in rpc.routes.values():
        cls = rpc.get_impl_class(spec.class_name)
        fn = getattr(cls, spec.method_name)
        resp_model = _response_model(fn)
        http = spec.http.upper()

        if http == "POST":
            BodyModel = _make_model_from_params(
                spec.class_name, spec.method_name, fn, mode="body"
            )

            async def endpoint(
                body: BodyModel = Body(...),  # type: ignore[name-defined]
                id: str | None = Query(default=None),
                _class_name=spec.class_name,
                _fn=fn,
            ):
                # If this class represents a long-lived instance (like Conversation),
                # allow 'id' or 'spec' creation. We detect presence
                # of 'id' or a field named 'id'.
                spec_payload = body.model_dump() if hasattr(body, "model_dump") else {}
                obj_id, inst = _ensure_instance(
                    _class_name,
                    spec_payload if "id" in spec_payload else None,
                    id,
                    model_registry,
                )
                # If we used spec for creation, remove
                # non-method args before calling the method:
                kwargs = body.model_dump()
                # Remove 'id' from kwargs if present; method likely doesn't want it
                kwargs.pop("id", None)
                result = _fn(inst, **kwargs)
                return WireCodec.to_wire(result)

            app.add_api_route(
                spec.path,
                endpoint,
                methods=["POST"],
                response_model=resp_model if isinstance(resp_model, type) else None,
                name=f"{spec.class_name}.{spec.method_name}",
            )

        elif http == "GET":
            QueryModel = _make_model_from_params(
                spec.class_name, spec.method_name, fn, mode="query"
            )

            async def endpoint(
                q: QueryModel = Depends(),  # type: ignore[name-defined]
                id: str | None = Query(default=None),
                _class_name=spec.class_name,
                _fn=fn,
            ):
                obj_id, inst = _ensure_instance(_class_name, None, id, model_registry)
                kwargs = q.model_dump()
                result = _fn(inst, **kwargs)
                return WireCodec.to_wire(result)

            app.add_api_route(
                spec.path,
                endpoint,
                methods=["GET"],
                response_model=resp_model if isinstance(resp_model, type) else None,
                name=f"{spec.class_name}.{spec.method_name}",
            )

        else:
            # Extend for PUT/PATCH/DELETE if needed
            pass

    # pre-seeded instances (optional)
    if instances:
        for k, v in instances.items():
            set_instance(k, v)

    return app
