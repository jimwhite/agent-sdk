"""
Hello World with Remote Sandboxed Agent Example

This example demonstrates:
1. Setting up a remote sandboxed agent server
2. Creating a conversation with the remote agent
3. Testing the execute_command functionality
4. Basic agent interaction in a sandboxed environment

This is a simple test to verify that the remote system mixin
execute_command method is working correctly.
"""

import os
import time

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Conversation,
    get_logger,
)
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.sdk.sandbox import DockerSandboxedAgentServer
from openhands.tools.preset.default import get_default_agent


logger = get_logger(__name__)


def main() -> None:
    # 1) Ensure we have LLM API key
    api_key = os.getenv("LITELLM_API_KEY")
    assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

    llm = LLM(
        service_id="agent",
        model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )

    # 2) Start the dev image in Docker via the SDK helper and wait for health
    with DockerSandboxedAgentServer(
        base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        host_port=8011,
        # TODO: Change this to your platform if not linux/arm64
        platform="linux/arm64",
    ) as server:
        # 3) Create agent
        agent = get_default_agent(
            llm=llm,
            working_dir="/",
            cli_mode=True,
        )

        # 4) Set up callback collection
        received_events: list = []
        last_event_time = {"ts": time.time()}

        def event_callback(event) -> None:
            event_type = type(event).__name__
            logger.info(f"🔔 Callback received event: {event_type}\n{event}")
            received_events.append(event)
            last_event_time["ts"] = time.time()

        # 5) Create RemoteConversation
        conversation = Conversation(
            agent=agent,
            host=server.base_url,
            callbacks=[event_callback],
            visualize=True,
        )
        assert isinstance(conversation, RemoteConversation)

        try:
            # Test the execute_command functionality
            logger.info("\n🔧 === TESTING EXECUTE_COMMAND ===")

            # Test 1: Simple command
            logger.info("🧪 Test 1: Basic echo command")
            result = conversation.execute_command(
                "echo 'Hello from remote sandboxed agent!'",
                cwd="/",
            )
            logger.info(f"✅ Command result: {result}")

            # Test 2: Command with output
            logger.info("🧪 Test 2: List directory contents")
            result = conversation.execute_command(
                "ls -la",
                cwd="/",
            )
            logger.info(f"✅ Directory listing: {result}")

            # Test 3: Command that creates a file
            logger.info("🧪 Test 3: Create and verify file")
            result = conversation.execute_command(
                "echo 'Test content' > /tmp/test_file.txt && cat /tmp/test_file.txt",
                cwd="/",
            )
            logger.info(f"✅ File creation result: {result}")

            # Test 4: Command with error
            logger.info("🧪 Test 4: Command that should fail")
            result = conversation.execute_command(
                "ls /nonexistent_directory",
                cwd="/",
            )
            logger.info(f"✅ Error command result: {result}")

            logger.info("\n🎉 All execute_command tests completed!")

        finally:
            print("\n🧹 Cleaning up conversation...")
            conversation.close()


if __name__ == "__main__":
    main()
