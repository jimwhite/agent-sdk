import argparse

import uvicorn

from openhands.agent_server.logging_config import LOGGING_CONFIG
from openhands.sdk.logger import DEBUG


def main():
    parser = argparse.ArgumentParser(description="OpenHands Agent Server App")
    parser.add_argument(
        "--mode",
        type=str,
        default="http",
        choices=["http", "acp"],
        help="Server mode: http for REST API, acp for Agent Client Protocol",
    )
    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        dest="reload",
        default=False,
        action="store_true",
        help="Enable auto-reload (disabled by default)",
    )
    parser.add_argument(
        "--persistence-dir",
        type=str,
        default="/tmp/openhands_conversations",
        help="Directory to store conversation data (ACP mode only)",
    )

    args = parser.parse_args()

    # Handle ACP mode
    if args.mode == "acp":
        import asyncio
        from pathlib import Path

        from openhands.agent_server.acp import ACPServer
        from openhands.agent_server.conversation_service import ConversationService

        print("🤖 Starting OpenHands Agent Server in ACP mode")
        print("📡 Listening on stdin/stdout for JSON-RPC messages")
        print(f"💾 Persistence directory: {args.persistence_dir}")
        print()

        async def run_acp():
            conversation_service = ConversationService(
                event_services_path=Path(args.persistence_dir),
                webhook_specs=[],
                session_api_key=None,
            )
            async with conversation_service:
                acp_server = ACPServer(conversation_service)
                try:
                    acp_server.run()
                except KeyboardInterrupt:
                    acp_server.stop()

        asyncio.run(run_acp())
        return

    # Handle HTTP mode (default)
    print(f"🙌 Starting OpenHands Agent Server on {args.host}:{args.port}")
    print(f"📖 API docs will be available at http://{args.host}:{args.port}/docs")
    print(f"🔄 Auto-reload: {'enabled' if args.reload else 'disabled'}")

    # Show debug mode status
    if DEBUG:
        print("🐛 DEBUG mode: ENABLED (stack traces will be shown)")
    else:
        print("🔒 DEBUG mode: DISABLED")
    print()

    # Configure uvicorn logging based on DEBUG environment variable
    log_level = "debug" if DEBUG else "info"

    uvicorn.run(
        "openhands.agent_server.api:api",
        host=args.host,
        port=args.port,
        reload=args.reload,
        reload_excludes=["workspace"],
        log_level=log_level,
        log_config=LOGGING_CONFIG,
    )


if __name__ == "__main__":
    main()
