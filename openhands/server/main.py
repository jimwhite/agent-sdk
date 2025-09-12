import hmac
import os
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from openhands.sdk.logger import get_logger
from openhands.server.routers.conversations import (
    active_conversations,
    router as conversations_router,
)


logger = get_logger(__name__)


# --- Lifespan Management for graceful shutdown ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up the OpenHands Agent Server...")
    yield
    logger.info("Shutting down... cleaning up active conversations.")
    for conv_id, conversation in active_conversations.items():
        logger.info(f"Closing conversation: {conv_id}")
        conversation.close()
    active_conversations.clear()


# --- FastAPI App Initialization ---
app = FastAPI(
    title="OpenHands Agent Server",
    description="An HTTP server to create and manage AI agent "
    "conversations using the OpenHands SDK.",
    version="1.0.0",
    lifespan=lifespan,
)


# --- API Endpoints ---
# --- Centralized exception handling ---
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log expected/client errors at warning level (no stack trace noise)
    logger.warning(
        "HTTPException: %s %s -> %s (%s)",
        request.method,
        request.url.path,
        exc.detail,
        exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log unexpected server errors with stack trace
    logger.exception(
        "Unhandled exception during %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


# ---------- Auth Middleware ----------


def _load_master_keys() -> list[str]:
    raw = os.getenv("MASTER_KEY", "x-your-api-key")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    return keys


class AuthMiddleware(BaseHTTPMiddleware):
    """Enforces X-Master-Key on all routes except allowlist."""

    def __init__(self, app, allowlist: list[str], header_name: str = "X-Master-Key"):
        super().__init__(app)
        self.allowlist = allowlist
        self.header_name = header_name
        self.keys = _load_master_keys()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable]
    ):
        # Allow OPTIONS (CORS preflight)
        if request.method.upper() == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"

        if path in self.allowlist:
            return await call_next(request)

        if not self.keys:
            return JSONResponse(
                status_code=500, content={"detail": "MASTER_KEY not configured"}
            )

        supplied = request.headers.get(self.header_name)
        if not supplied:
            return JSONResponse(
                status_code=401, content={"detail": "Unauthorized: missing master key"}
            )

        if not any(hmac.compare_digest(supplied, k) for k in self.keys):
            return JSONResponse(
                status_code=401, content={"detail": "Unauthorized: invalid master key"}
            )

        return await call_next(request)


@app.get("/health", summary="Health Check")
async def health_check():
    return {"status": "ok"}


app.add_middleware(
    AuthMiddleware,
    allowlist=["/health", "/docs", "/openapi.json"],
)

# --- Include Routers ---
app.include_router(conversations_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
