"""
Enhanced Hello World with Sandboxed Server Example

This example demonstrates:
1. Direct bash command execution with the improved execute_command method
2. Agent conversation capabilities in a sandboxed environment
3. Verification of agent work using direct bash commands
4. Error handling and comprehensive logging

The example shows how you can:
- Execute bash commands directly and get complete results (exit code, output)
- Run agent conversations that can interact with the sandboxed environment
- Verify and inspect the agent's work using direct system commands
- Handle both successful operations and error conditions

This showcases the dual nature of the sandboxed server: it can both host
agent conversations AND provide direct programmatic access to the environment.
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
    #    Forward LITELLM_API_KEY into the container so remote tools can use it.
    with DockerSandboxedAgentServer(
        base_image="nikolaik/python-nodejs:python3.12-nodejs22",
        host_port=8010,
        # TODO: Change this to your platform if not linux/arm64
        platform="linux/arm64",
    ) as server:
        # 3) Create agent – IMPORTANT: working_dir must be the path inside container
        #    where we mounted the current repo.
        agent = get_default_agent(
            llm=llm,
            working_dir="/",
            cli_mode=True,
        )

        # 4) Set up callback collection, like example 22
        received_events: list = []
        last_event_time = {"ts": time.time()}

        def event_callback(event) -> None:
            event_type = type(event).__name__
            logger.info(f"🔔 Callback received event: {event_type}\n{event}")
            received_events.append(event)
            last_event_time["ts"] = time.time()

        # 5) Create RemoteConversation and do the same 2-step task
        conversation = Conversation(
            agent=agent,
            host=server.base_url,
            callbacks=[event_callback],
            visualize=True,
        )
        assert isinstance(conversation, RemoteConversation)

        try:
            # First, demonstrate direct bash execution capabilities
            logger.info("\n🔧 === DEMONSTRATING DIRECT BASH EXECUTION ===")

            # Test 1: Simple command with successful output
            logger.info("🧪 Test 1: Basic command execution")
            result = conversation.execute_command(
                "echo 'Hello from sandboxed environment!' && pwd",
                cwd="/",
            )
            logger.info(f"✅ Command completed: {result}")
        finally:
            print("\n🧹 Cleaning up conversation...")
            conversation.close()


if __name__ == "__main__":
    main()
