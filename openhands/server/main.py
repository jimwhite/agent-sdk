# openhands/server/main.py
import argparse
import importlib
import sys

from pydantic import BaseModel

# --- Import SDK models you want exposed in OpenAPI / wire codec ---
# Add/remove as your SDK grows.
from openhands.sdk import Message, TextContent
from openhands.server.app import build_app


# Avoid importing heavy models at import time; load lazily in create_model_registry
LLM = None  # type: ignore[assignment]
Agent = None  # type: ignore[assignment]
Conversation = None  # type: ignore[assignment]


# # --- Ensure server-side implementations are imported so @rpc decorators register ---
# # Import modules with route-decorated implementations.
# Keep this list small & explicit.
# # If you add more services, import them here so their decorators run at startup.
IMPLEMENTATION_MODULES: list[str] = []


def create_model_registry() -> dict[str, type[BaseModel]]:
    """Models that may appear in request/response bodies for (de)serialization."""
    global LLM, Agent, Conversation
    if LLM is None or Agent is None or Conversation is None:
        from openhands.sdk import (
            LLM as _LLM,
            Agent as _Agent,
            Conversation as _Conversation,
        )

        LLM, Agent, Conversation = _LLM, _Agent, _Conversation

    return {
        "Agent": Agent,  # type: ignore[arg-type]
        "Conversation": Conversation,  # type: ignore[arg-type]
        "LLM": LLM,  # type: ignore[arg-type]
        "Message": Message,
        "TextContent": TextContent,
    }


def import_implementations(modules: list[str]) -> None:
    """Import implementation modules for side-effect decorator registration."""
    for m in modules:
        importlib.import_module(m)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="openhandsd",
        description="OpenHands HTTP server",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)"
    )
    parser.add_argument("--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (dev only)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of Uvicorn workers (ignored if --reload)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        help="Log level",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    # Import implementations so @rpc.service/@rpc.method are registered
    import_implementations(IMPLEMENTATION_MODULES)

    # Build FastAPI app from registered routes & models
    app = build_app(model_registry=create_model_registry(), instances={})

    # Lazy import to avoid import-time dependency during testing
    import uvicorn  # type: ignore

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        reload=args.reload,
        workers=None if args.reload else args.workers,
    )


if __name__ == "__main__":
    run()
