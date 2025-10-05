"""Example demonstrating APIRemoteWorkspace with conversation and Runtime API.

This example shows:
1. Using APIRemoteWorkspace to run agent-server in remote sandboxed environment
2. Running agent conversations with the remote workspace
3. Different modes: base image, pre-built image, or building via Runtime API

Environment Variables:
- LITELLM_API_KEY: Required for LLM access
- RUNTIME_API_KEY: Required for Runtime API access
- USE_PREBUILT_IMAGE: Set to "true" to use pre-built agent-server image (recommended)
- BUILD_AGENT_SERVER: Set to "true" to build agent-server via
    Runtime API (may fail due to size limits)

Usage Examples:
  # Use pre-built image (recommended - avoids Runtime API size limits)
  USE_PREBUILT_IMAGE=true uv run examples/24_remote_convo_with_api_sandboxed_server.py

  # Use base image only (will fail if base image doesn't have agent-server)
  uv run examples/24_remote_convo_with_api_sandboxed_server.py

  # Attempt to build via Runtime API (will fail due to ~512 KB size limit)
  BUILD_AGENT_SERVER=true uv run examples/24_remote_convo_with_api_sandboxed_server.py

Note: All endpoint and method issues have been fixed. If pods remain in "Pending" state,
this indicates a Runtime API service issue (image pull failure or resource constraints).
See FIXES_SUMMARY.md for complete details.
"""

import os
import time

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Conversation,
    RemoteConversation,
    get_logger,
)
from openhands.sdk.workspace import APIRemoteWorkspace
from openhands.tools.preset.default import get_default_agent


logger = get_logger(__name__)


def main() -> None:
    # 1) Ensure we have LLM API key
    api_key = os.getenv("LITELLM_API_KEY")
    assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

    llm = LLM(
        service_id="agent",
        model="litellm_proxy/anthropic/claude-sonnet-4-5-20250929",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )

    # 2) Check if we should build agent-server image
    runtime_api_key = os.getenv("RUNTIME_API_KEY")
    if not runtime_api_key:
        logger.error("RUNTIME_API_KEY not set, cannot create APIRemoteWorkspace")
        return

    # Check for different modes
    build_agent_server = os.getenv("BUILD_AGENT_SERVER", "false").lower() == "true"
    use_prebuilt = os.getenv("USE_PREBUILT_IMAGE", "false").lower() == "true"

    # Use the Runtime API docker repo (required by the API)
    registry_prefix = (
        "us-central1-docker.pkg.dev/evaluation-092424/runtime-api-docker-repo"
    )

    logger.info("\n" + "=" * 80)
    logger.info("🚀 Starting Conversation with APIRemoteWorkspace")
    logger.info("=" * 80)

    if use_prebuilt:
        logger.info("📦 Using pre-built agent-server image from ghcr.io")
        logger.info("   This avoids the Runtime API size limit for build contexts")
        # Use a verified pre-built agent-server image
        base_image = "ghcr.io/all-hands-ai/agent-server:99212f0-custom-dev"
        logger.info(f"   Image: {base_image}")
    elif build_agent_server:
        logger.info(
            "🔨 Build mode: Will attempt to build agent-server image via Runtime API"
        )
        logger.info(
            "   ⚠️  WARNING: This will likely fail due to "
            "Runtime API size limit (~512 KB)"
        )
        logger.info(f"   Registry: {registry_prefix}")
        logger.info(
            "   💡 TIP: Use USE_PREBUILT_IMAGE=true to use "
            "a working pre-built image instead"
        )
        base_image = "nikolaik/python-nodejs:python3.12-nodejs22"
    else:
        logger.info("📦 Using base image without agent-server")
        logger.info(
            "   ⚠️  This will fail if the base image doesn't have agent-server installed"
        )
        logger.info(
            "   💡 TIP: Use USE_PREBUILT_IMAGE=true to use a working pre-built image"
        )
        base_image = "nikolaik/python-nodejs:python3.12-nodejs22"

    # 3) Create an API-based remote workspace with automatic building if enabled
    with APIRemoteWorkspace(
        api_url="https://runtime.eval.all-hands.dev",
        runtime_api_key=runtime_api_key,
        base_image=base_image,
        working_dir="/workspace",
        # Auto-build configuration (only takes effect if
        # build_agent_server=True and not use_prebuilt)
        build_agent_server=build_agent_server and not use_prebuilt,
        registry_prefix=registry_prefix
        if (build_agent_server and not use_prebuilt)
        else None,
    ) as workspace:
        logger.info(f"✅ Workspace ready using image: {workspace.base_image}")

        # 4) Create agent
        agent = get_default_agent(
            llm=llm,
            cli_mode=True,
        )

        # 5) Set up callback collection
        received_events: list = []
        last_event_time = {"ts": time.time()}

        def event_callback(event) -> None:
            event_type = type(event).__name__
            logger.info(f"🔔 Callback received event: {event_type}\n{event}")
            received_events.append(event)
            last_event_time["ts"] = time.time()

        # 6) Test the workspace with a simple command
        result = workspace.execute_command(
            "echo 'Hello from sandboxed environment!' && pwd"
        )
        logger.info(
            f"Command '{result.command}' completed with exit code {result.exit_code}"
        )
        logger.info(f"Output: {result.stdout}")

        # 7) Start conversation
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
            callbacks=[event_callback],
            visualize=True,
        )
        assert isinstance(conversation, RemoteConversation)

        try:
            logger.info(f"\n📋 Conversation ID: {conversation.state.id}")

            logger.info("📝 Sending first message...")
            conversation.send_message(
                "Read the current repo and write 3 facts about the project into "
                "FACTS.txt."
            )
            logger.info("🚀 Running conversation...")
            conversation.run()
            logger.info("✅ First task completed!")
            logger.info(f"Agent status: {conversation.state.agent_status}")

            # Wait for events to settle (no events for 2 seconds)
            logger.info("⏳ Waiting for events to stop...")
            while time.time() - last_event_time["ts"] < 2.0:
                time.sleep(0.1)
            logger.info("✅ Events have stopped")

            logger.info("🚀 Running conversation again...")
            conversation.send_message("Great! Now delete that file.")
            conversation.run()
            logger.info("✅ Second task completed!")
        finally:
            print("\n🧹 Cleaning up conversation...")
            conversation.close()


if __name__ == "__main__":
    main()
