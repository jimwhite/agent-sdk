"""Authentication middleware for the OpenHands Agent SDK server."""

from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for master key authentication.

    Validates Bearer token against master key for all endpoints except /alive.
    """

    def __init__(self, app, master_key: str):
        super().__init__(app)
        self.master_key = master_key
        self.excluded_paths = {"/alive", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and validate authentication.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response
        """
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "MissingAuthorization",
                    "message": "Authorization header is required",
                },
            )

        # Validate Bearer token format
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "InvalidAuthorizationFormat",
                    "message": "Authorization header must use Bearer token format",
                },
            )

        # Extract and validate token
        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != self.master_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "InvalidMasterKey",
                    "message": "Invalid master key provided",
                },
            )

        # Authentication successful, proceed with request
        return await call_next(request)
