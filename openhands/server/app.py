# app.py
import inspect
import os
import uuid
from typing import Any, get_type_hints

from fastapi import Body, Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, create_model

# Import Agent and tools to ensure they're registered in the discriminated union
from openhands.sdk.rpc import api
from openhands.sdk.rpc.wire import WireCodec
from openhands.server.state import get_instance, set_instance


# Import tool action/observation classes for discriminated union registration


# ---- authentication --------------------------------------------------------

security = HTTPBearer()


def verify_auth(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the OPENHANDS_MASTER_KEY."""
    expected_key = os.environ.get("OPENHANDS_MASTER_KEY")
    if not expected_key:
        raise HTTPException(401, "OPENHANDS_MASTER_KEY not configured")
    if credentials.credentials != expected_key:
        raise HTTPException(401, "Invalid API key")
    return credentials


# ---- helpers to build request/response models from annotated methods --------


def _make_model_from_params(
    cls_name: str, method_name: str, fn, *, mode: str
) -> type[BaseModel]:
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn)
    except NameError:
        # Handle forward references that can't be resolved
        hints = {}
        for param_name, param in sig.parameters.items():
            if param.annotation != inspect.Parameter.empty:
                if isinstance(param.annotation, str):
                    # Forward reference - use Any for now
                    hints[param_name] = Any
                else:
                    hints[param_name] = param.annotation
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
    """Create a Conversation instance on the server and return its id."""

    id: str | None = None
    spec: dict[str, Any] | None = None


def _ensure_instance(
    class_name: str,
    spec: dict[str, Any] | None,
    id_: str | None,
    model_registry: dict[str, type[BaseModel]],
):
    cls = api.get_impl_class(class_name)

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
        # Map incoming 'id' to the constructor parameter if needed
        if isinstance(kwargs, dict):
            _id = kwargs.pop("id", None)
            if _id and "conversation_id" not in kwargs:
                kwargs["conversation_id"] = conv_id
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
    api.collect()

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Discovery for clients (renamed from /rpc/schema to /api/schema)
    @app.get("/api/schema")
    def schema():
        return [
            {
                "class": s.class_name,
                "method": s.method_name,
                "http": s.http,
                "path": s.path,
                "instance_scoped": s.instance_scoped,
                "request_in": s.request_in,
                "auth_required": s.auth_required,
            }
            for s in api.routes.values()
        ]

    # Health check endpoint (no auth required)
    @app.get("/alive")
    def alive():
        return {"ok": True}

    # Auto-generate constructor routes for services
    for cls_name, cls in api._impls.items():
        if cls_name == "Conversation":  # Only handle Conversation for now
            # Create constructor route POST /conversation
            ConstructorModel = _make_model_from_params(
                cls_name, "__init__", cls.__init__, mode="body"
            )

            async def constructor_endpoint(
                body: ConstructorModel = Body(...),  # type: ignore[name-defined]
                _cls=cls,
                _cls_name=cls_name,
            ):
                # Generate ID if not provided
                kwargs = body.model_dump()

                # Manually deserialize the agent if it's a dict
                if "agent" in kwargs and isinstance(kwargs["agent"], dict):
                    try:
                        from openhands.sdk.agent import Agent
                        from openhands.sdk.llm import LLM

                        agent_data = kwargs["agent"]
                        print(f"DEBUG: Agent data: {agent_data}")

                        # If it's WireCodec format, extract the data
                        if "__model__" in agent_data:
                            agent_data = agent_data["data"]

                        # Deserialize the LLM if it's nested
                        if "llm" in agent_data and isinstance(agent_data["llm"], dict):
                            llm_data = agent_data["llm"]
                            if "__model__" in llm_data:
                                llm_data = llm_data["data"]
                            agent_data["llm"] = LLM.model_validate(llm_data)

                        # Create the Agent instance
                        kwargs["agent"] = Agent.model_validate(agent_data)
                        print("DEBUG: Successfully created Agent instance")

                    except Exception as e:
                        print(f"DEBUG: Agent deserialization error: {e}")
                        # Fall back to raw dict if deserialization fails
                        pass

                conv_id = kwargs.pop("conversation_id", None) or str(uuid.uuid4())

                # Map id to conversation_id if needed
                if "id" in kwargs:
                    kwargs["conversation_id"] = kwargs.pop("id")

                # Create instance
                inst = _cls(**kwargs)
                set_instance(conv_id, inst)
                return {"id": conv_id}

            app.add_api_route(
                "/conversation",
                constructor_endpoint,
                methods=["POST"],
                dependencies=[Depends(verify_auth)],
                name=f"{cls_name}.create",
            )

    # Generate method routes from @api.method decorators
    for spec in api.routes.values():
        cls = api.get_impl_class(spec.class_name)
        fn = getattr(cls, spec.method_name)
        resp_model = _response_model(fn)
        http = spec.http.upper()

        # Prepare dependencies
        dependencies = []
        if spec.auth_required:
            dependencies.append(Depends(verify_auth))

        if http == "POST":
            if spec.instance_scoped and "{id}" in spec.path:
                # Instance-scoped POST method
                BodyModel = _make_model_from_params(
                    spec.class_name, spec.method_name, fn, mode="body"
                )

                async def post_endpoint(
                    id: str,
                    body: BodyModel | None = Body(default=None),  # type: ignore[name-defined]
                    _fn=fn,
                ):
                    inst = get_instance(id)
                    if inst is None:
                        raise HTTPException(404, f"Instance {id} not found")

                    kwargs = body.model_dump() if body else {}

                    # Deserialize any SDK models in the kwargs
                    try:
                        from openhands.sdk.agent import Agent
                        from openhands.sdk.llm import LLM, Message

                        # Handle common SDK models
                        for key, value in kwargs.items():
                            if isinstance(value, dict):
                                # Try to deserialize Message objects
                                if key == "message" and "role" in value:
                                    kwargs[key] = Message.model_validate(value)
                                # Handle WireCodec format
                                elif "__model__" in value:
                                    model_name = value["__model__"]
                                    if model_name == "Message":
                                        kwargs[key] = Message.model_validate(
                                            value["data"]
                                        )
                                    elif model_name == "Agent":
                                        kwargs[key] = Agent.model_validate(
                                            value["data"]
                                        )
                                    elif model_name == "LLM":
                                        kwargs[key] = LLM.model_validate(value["data"])
                    except Exception as e:
                        print(f"DEBUG: Method deserialization error: {e}")
                        # Fall back to raw dict if deserialization fails
                        pass

                    result = _fn(inst, **kwargs)
                    return WireCodec.to_wire(result) if result is not None else None

                app.add_api_route(
                    spec.path,
                    post_endpoint,
                    methods=["POST"],
                    response_model=resp_model if isinstance(resp_model, type) else None,
                    dependencies=dependencies,
                    name=f"{spec.class_name}.{spec.method_name}",
                )
            else:
                # Non-instance-scoped POST method (not implemented yet)
                pass

        elif http == "GET":
            if spec.instance_scoped and "{id}" in spec.path:
                # Instance-scoped GET method
                QueryModel = _make_model_from_params(
                    spec.class_name, spec.method_name, fn, mode="query"
                )

                async def get_endpoint(
                    id: str,
                    q: QueryModel = Depends(),  # type: ignore[name-defined]
                    _fn=fn,
                ):
                    inst = get_instance(id)
                    if inst is None:
                        raise HTTPException(404, f"Instance {id} not found")

                    kwargs = q.model_dump()
                    result = _fn(inst, **kwargs)
                    return WireCodec.to_wire(result) if result is not None else None

                app.add_api_route(
                    spec.path,
                    get_endpoint,
                    methods=["GET"],
                    response_model=resp_model if isinstance(resp_model, type) else None,
                    dependencies=dependencies,
                    name=f"{spec.class_name}.{spec.method_name}",
                )
            else:
                # Non-instance-scoped GET method (not implemented yet)
                pass

        else:
            # Extend for PUT/PATCH/DELETE if needed
            pass

    # pre-seeded instances (optional)
    if instances:
        for k, v in instances.items():
            set_instance(k, v)

    return app
