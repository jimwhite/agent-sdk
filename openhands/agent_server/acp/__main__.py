"""CLI entry point for ACP server."""

import asyncio
import os
from pathlib import Path

from openhands.agent_server.conversation_service import ConversationService

from .server import ACPServer


async def main() -> None:
    """Main entry point for ACP server."""
    # Initialize conversation service
    persistence_dir = os.getenv(
        "OPENHANDS_PERSISTENCE_DIR", "/tmp/openhands_conversations"
    )
    conversation_service = ConversationService(
        event_services_path=Path(persistence_dir),
        webhook_specs=[],
        session_api_key=None,
    )

    # Start conversation service context
    async with conversation_service:
        # Create and run ACP server
        server = ACPServer(conversation_service)
        try:
            server.run()
        except KeyboardInterrupt:
            server.stop()


if __name__ == "__main__":
    asyncio.run(main())
