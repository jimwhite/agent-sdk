"""
AsyncAPI documentation router for OpenHands Agent Server.

Provides endpoints to serve AsyncAPI documentation for WebSocket endpoints,
similar to how FastAPI serves OpenAPI documentation for REST endpoints.
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from openhands.agent_server.asyncapi_schema import (
    generate_asyncapi_schema,
    generate_asyncapi_yaml,
)


asyncapi_router = APIRouter(prefix="/asyncapi", tags=["AsyncAPI Documentation"])


@asyncapi_router.get("/asyncapi.json", response_class=JSONResponse)
async def get_asyncapi_json(request: Request) -> JSONResponse:
    """
    Get AsyncAPI schema as JSON.

    Returns the complete AsyncAPI 3.0.0 schema documenting the WebSocket
    endpoints for conversation events and bash events.
    """
    # Determine the server URL from the request
    server_url = f"ws://{request.headers.get('host', 'localhost:8000')}"

    schema = generate_asyncapi_schema(
        server_url=server_url,
        title="OpenHands Agent Server WebSocket API",
        version="1.0.0",
    )

    return JSONResponse(content=schema)


@asyncapi_router.get("/asyncapi.yaml", response_class=PlainTextResponse)
async def get_asyncapi_yaml(request: Request) -> PlainTextResponse:
    """
    Get AsyncAPI schema as YAML.

    Returns the complete AsyncAPI 3.0.0 schema in YAML format documenting
    the WebSocket endpoints for conversation events and bash events.
    """
    # Determine the server URL from the request
    server_url = f"ws://{request.headers.get('host', 'localhost:8000')}"

    try:
        yaml_content = generate_asyncapi_yaml(
            server_url=server_url,
            title="OpenHands Agent Server WebSocket API",
            version="1.0.0",
        )
        return PlainTextResponse(content=yaml_content, media_type="text/yaml")
    except ImportError:
        return PlainTextResponse(
            content="YAML output requires PyYAML. Install with: pip install pyyaml",
            status_code=500,
        )


@asyncapi_router.get("/", response_class=JSONResponse)
async def get_asyncapi_info() -> JSONResponse:
    """
    Get information about available AsyncAPI documentation endpoints.

    Returns links to the AsyncAPI schema in different formats and
    information about AsyncAPI Studio for viewing the documentation.
    """
    return JSONResponse(
        content={
            "title": "OpenHands Agent Server AsyncAPI Documentation",
            "description": (
                "AsyncAPI documentation for WebSocket endpoints. "
                "Use AsyncAPI Studio or other AsyncAPI tools to view the documentation."
            ),
            "asyncapi_version": "3.0.0",
            "endpoints": {
                "json": "/asyncapi/asyncapi.json",
                "yaml": "/asyncapi/asyncapi.yaml",
                "studio": "/asyncapi/studio",
            },
            "tools": {
                "asyncapi_studio": {
                    "url": "https://studio.asyncapi.com/",
                    "description": (
                        "Paste the JSON or YAML schema URL into AsyncAPI Studio "
                        "to view interactive documentation."
                    ),
                },
                "asyncapi_generator": {
                    "url": "https://github.com/asyncapi/generator",
                    "description": (
                        "Use AsyncAPI Generator to create client code, "
                        "documentation, and more from the schema."
                    ),
                },
            },
            "websocket_endpoints": {
                "conversation_events": {
                    "path": "/sockets/events/{conversation_id}",
                    "description": "Real-time conversation events and message exchange",
                },
                "bash_events": {
                    "path": "/sockets/bash-events",
                    "description": "Real-time bash command execution events",
                },
            },
        }
    )


@asyncapi_router.get("/studio")
async def get_asyncapi_studio() -> FileResponse:
    """
    Serve AsyncAPI Studio interface for interactive documentation.

    Returns:
        HTML page with embedded AsyncAPI Studio that loads the local schema.
    """
    # Get the path to the static HTML file
    current_dir = Path(__file__).parent
    studio_file = current_dir / "static" / "asyncapi-studio.html"

    if not studio_file.exists():
        # Fallback: return a simple redirect to AsyncAPI Studio with schema URL
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="AsyncAPI Studio interface not found. "
            "You can view the documentation at https://studio.asyncapi.com/ "
            "by loading the schema from /asyncapi/asyncapi.json",
        )

    return FileResponse(
        path=str(studio_file),
        media_type="text/html",
        filename="asyncapi-studio.html",
    )
