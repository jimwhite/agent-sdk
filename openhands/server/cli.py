#!/usr/bin/env python3
"""CLI entry point for OpenHands Agent SDK Server."""

import argparse
import os
import sys

import uvicorn


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
