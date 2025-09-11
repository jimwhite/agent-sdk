"""Main FastAPI application for the OpenHands Agent SDK server."""

import os
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from openhands.server.middleware.auth import AuthMiddleware
from openhands.server.models.responses import StatusResponse
from openhands.server.routers import conversations


# Validate master key
master_key = os.getenv("OPENHANDS_MASTER_KEY")
if not master_key:
    raise ValueError(
        "OPENHANDS_MASTER_KEY environment variable is required. "
        "Please set it to a secure random string."
    )

# Create FastAPI app
app = FastAPI(
    title="OpenHands Agent SDK API",
    description=(
        "REST API with 1-1 mapping to Conversation class methods. "
        "Automatically generated from the SDK class definitions."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add authentication middleware
app.add_middleware(AuthMiddleware, master_key=master_key)

# Include conversation router
app.include_router(
    conversations.router, prefix="/conversations", tags=["conversations"]
)


# Health check endpoint (no auth required)
@app.get("/alive", response_model=StatusResponse, tags=["health"])
async def health_check() -> StatusResponse:
    """Health check endpoint.

    This endpoint does not require authentication and can be used
    for load balancer health checks.

    Returns:
        StatusResponse indicating server is alive
    """
    return StatusResponse(
        status="alive", message="OpenHands Agent SDK server is running"
    )


# Stats endpoint for monitoring
@app.get("/stats", response_model=Dict[str, Any], tags=["monitoring"])
async def get_stats() -> Dict[str, Any]:
    """Get server statistics.

    Returns:
        Dictionary with server and conversation statistics
    """
    from openhands.server.routers.conversations import get_conversation_manager

    manager = get_conversation_manager()
    return {
        "server": {"status": "running", "version": "1.0.0"},
        "conversations": manager.get_stats(),
    }


# Custom OpenAPI schema generation
def custom_openapi():
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    # Generate base schema from FastAPI
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add authentication scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "description": (
                "Master key authentication. Set OPENHANDS_MASTER_KEY "
                "environment variable and use it as Bearer token."
            ),
        }
    }

    # Apply security to all endpoints except excluded ones
    excluded_paths = {"/alive", "/docs", "/redoc", "/openapi.json"}
    for path, methods in openapi_schema["paths"].items():
        if path not in excluded_paths:
            for method_info in methods.values():
                if isinstance(method_info, dict):
                    method_info["security"] = [{"BearerAuth": []}]

    # Add custom tags and descriptions
    openapi_schema["tags"] = [
        {
            "name": "conversations",
            "description": (
                "Conversation management with 1-1 mapping to Conversation class methods"
            ),
        },
        {"name": "health", "description": "Health check and monitoring endpoints"},
        {"name": "monitoring", "description": "Server statistics and monitoring"},
    ]

    # Add server information
    openapi_schema["servers"] = [
        {"url": "http://localhost:9000", "description": "Development server"}
    ]

    # Add additional info
    openapi_schema["info"]["contact"] = {
        "name": "OpenHands Team",
        "url": "https://github.com/All-Hands-AI/agent-sdk",
    }

    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "details": {"type": type(exc).__name__},
        },
    )


if __name__ == "__main__":
    import uvicorn

    # Configuration from environment variables
    host = os.getenv("OPENHANDS_SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("OPENHANDS_SERVER_PORT", "9000"))
    log_level = os.getenv("OPENHANDS_LOG_LEVEL", "info").lower()

    print(f"Starting OpenHands Agent SDK server on {host}:{port}")
    print(f"Log level: {log_level}")
    print("Make sure OPENHANDS_MASTER_KEY environment variable is set!")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        reload=False,  # Set to True for development
    )
