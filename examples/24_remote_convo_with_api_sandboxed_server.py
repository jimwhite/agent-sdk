"""Example: APIRemoteWorkspace with Runtime API.

Usage:
  USE_PREBUILT_IMAGE=true uv run examples/24_remote_convo_with_api_sandboxed_server.py
"""  # noqa: E501

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
    api_key = os.getenv("LITELLM_API_KEY")
    assert api_key, "LITELLM_API_KEY required"

    llm = LLM(
        service_id="agent",
        model="litellm_proxy/anthropic/claude-sonnet-4-5-20250929",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )

    runtime_api_key = os.getenv("RUNTIME_API_KEY")
    if not runtime_api_key:
        logger.error("RUNTIME_API_KEY required")
        return

    build_agent_server = os.getenv("BUILD_AGENT_SERVER", "false").lower() == "true"
    use_prebuilt = os.getenv("USE_PREBUILT_IMAGE", "false").lower() == "true"
    registry_prefix = (
        "us-central1-docker.pkg.dev/evaluation-092424/runtime-api-docker-repo"
    )

    base_image = (
        "ghcr.io/all-hands-ai/agent-server:99212f0-custom-dev"
        if use_prebuilt
        else "nikolaik/python-nodejs:python3.12-nodejs22"
    )

    with APIRemoteWorkspace(
        api_url="https://runtime.eval.all-hands.dev",
        runtime_api_key=runtime_api_key,
        base_image=base_image,
        working_dir="/workspace",
        build_agent_server=build_agent_server and not use_prebuilt,
        registry_prefix=registry_prefix
        if (build_agent_server and not use_prebuilt)
        else None,
    ) as workspace:
        agent = get_default_agent(llm=llm, cli_mode=True)
        received_events: list = []
        last_event_time = {"ts": time.time()}

        def event_callback(event) -> None:
            received_events.append(event)
            last_event_time["ts"] = time.time()

        result = workspace.execute_command(
            "echo 'Hello from sandboxed environment!' && pwd"
        )
        logger.info(f"Command completed: {result.exit_code}, {result.stdout}")

        conversation = Conversation(
            agent=agent, workspace=workspace, callbacks=[event_callback], visualize=True
        )
        assert isinstance(conversation, RemoteConversation)

        try:
            conversation.send_message(
                "Read the current repo and write 3 facts about the project into"
                " FACTS.txt."
            )
            conversation.run()

            while time.time() - last_event_time["ts"] < 2.0:
                time.sleep(0.1)

            conversation.send_message("Great! Now delete that file.")
            conversation.run()
        finally:
            conversation.close()


if __name__ == "__main__":
    main()
