#!/usr/bin/env python3
"""CLI entry point for OpenHands Agent SDK Server."""

import argparse
import importlib.util
import os
import sys
import types
from typing import Any, Dict

import uvicorn


# Handle missing litellm modules first (before any imports that might trigger litellm)
class MockModule(types.ModuleType):
    """A dynamic mock module that creates submodules and attributes on demand."""

    def __getattr__(self, name: str) -> Any:
        # Create a new mock module or class on demand
        if name.endswith("Base") or name[0].isupper():
            # Looks like a class name
            mock_class = type(name, (), {"__init__": lambda self, **kwargs: None})
            setattr(self, name, mock_class)
            return mock_class
        else:
            # Looks like a module name
            full_name = f"{self.__name__}.{name}" if hasattr(self, "__name__") else name
            mock_module = MockModule(full_name)
            setattr(self, name, mock_module)
            sys.modules[full_name] = mock_module
            return mock_module

    def __iter__(self):
        """Make the module iterable (return empty iterator)."""
        return iter([])

    def __len__(self):
        """Make the module have a length."""
        return 0


# Create the main integrations module
litellm_integrations = MockModule("litellm.integrations")
sys.modules["litellm.integrations"] = litellm_integrations

if importlib.util.find_spec("fastmcp") is None:
    # Create a Pydantic-compatible mock MCPConfig
    class MockMCPConfig:
        """Mock MCPConfig class that's compatible with Pydantic."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

        @classmethod
        def __get_pydantic_core_schema__(
            cls, source_type: Any, handler: Any
        ) -> Dict[str, Any]:
            """Provide a Pydantic core schema for the mock class."""
            return {
                "type": "dict",
                "keys_schema": {"type": "str"},
                "values_schema": {"type": "any"},
            }

    class MockLogMessage:
        """Mock LogMessage class."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    class MockClient:
        """Mock Client class."""

        def __init__(self, **kwargs: Any) -> None:
            for key, value in kwargs.items():
                setattr(self, key, value)

    fastmcp = types.ModuleType("fastmcp")
    setattr(fastmcp, "Client", MockClient)
    fastmcp_mcp_config = types.ModuleType("mcp_config")
    setattr(fastmcp_mcp_config, "MCPConfig", MockMCPConfig)
    setattr(fastmcp, "mcp_config", fastmcp_mcp_config)
    fastmcp_client = types.ModuleType("client")
    fastmcp_client_logging = types.ModuleType("logging")
    setattr(fastmcp_client_logging, "LogMessage", MockLogMessage)
    setattr(fastmcp_client, "logging", fastmcp_client_logging)
    setattr(fastmcp, "client", fastmcp_client)
    sys.modules["fastmcp"] = fastmcp
    sys.modules["fastmcp.mcp_config"] = fastmcp_mcp_config
    sys.modules["fastmcp.client"] = fastmcp_client
    sys.modules["fastmcp.client.logging"] = fastmcp_client_logging


def main() -> None:
    """Main CLI entry point for the server."""
    parser = argparse.ArgumentParser(
        description="OpenHands Agent SDK Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  OPENHANDS_MASTER_KEY    Master key for API authentication (required)
  OPENHANDS_DEBUG         Enable debug mode (optional, default: false)

Examples:
  %(prog)s --host 0.0.0.0 --port 8000
  %(prog)s --host localhost --port 3000 --workers 4
        """,
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server to (default: 8000)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    parser.add_argument(
        "--log-level",
        choices=["critical", "error", "warning", "info", "debug", "trace"],
        default="info",
        help="Log level (default: info)",
    )
    parser.add_argument(
        "--access-log",
        action="store_true",
        help="Enable access log",
    )

    args = parser.parse_args()

    # Check for required environment variables
    master_key = os.getenv("OPENHANDS_MASTER_KEY")
    if not master_key:
        print(
            "Error: OPENHANDS_MASTER_KEY environment variable is required",
            file=sys.stderr,
        )
        print("Please set it before running the server:", file=sys.stderr)
        print("  export OPENHANDS_MASTER_KEY='your-secret-key'", file=sys.stderr)
        sys.exit(1)

    # Print startup information
    print(f"Starting OpenHands Agent SDK Server on {args.host}:{args.port}")
    print(f"Master key configured: {'✓' if master_key else '✗'}")
    print(f"Debug mode: {'✓' if os.getenv('OPENHANDS_DEBUG') else '✗'}")
    print(f"Workers: {args.workers}")
    print(f"Log level: {args.log_level}")
    print()
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"OpenAPI Spec: http://{args.host}:{args.port}/openapi.json")
    print(f"Health Check: http://{args.host}:{args.port}/alive")
    print()

    # Start the server
    try:
        uvicorn.run(
            "openhands.server.main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=args.reload,
            log_level=args.log_level,
            access_log=args.access_log,
        )
    except KeyboardInterrupt:
        print("\nShutting down server...")
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
