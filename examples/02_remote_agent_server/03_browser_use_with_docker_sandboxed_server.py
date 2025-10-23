import os
import platform
import time

from pydantic import SecretStr

from openhands.sdk import LLM, Conversation, get_logger
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.tools.preset.default import get_default_agent
from openhands.workspace import DockerWorkspace


logger = get_logger(__name__)


api_key = os.getenv("LLM_API_KEY")
assert api_key is not None, "LLM_API_KEY environment variable is not set."

llm = LLM(
    usage_id="agent",
    model="litellm_proxy/anthropic/claude-sonnet-4-5-20250929",
    base_url="https://llm-proxy.eval.all-hands.dev",
    api_key=SecretStr(api_key),
)


def detect_platform():
    """Detects the correct Docker platform string."""
    machine = platform.machine().lower()
    if "arm" in machine or "aarch64" in machine:
        return "linux/arm64"
    return "linux/amd64"


# Create a Docker-based remote workspace with extra ports for browser access
with DockerWorkspace(
    base_image="nikolaik/python-nodejs:python3.12-nodejs22",
    host_port=8010,
    # TODO: Change this to your platform if not linux/arm64
    platform=detect_platform(),
    extra_ports=True,  # Expose extra ports for VSCode and VNC
) as workspace:
    """Extra ports allows you to check localhost:8012 for VNC"""

    # Create agent with browser tools enabled
    agent = get_default_agent(
        llm=llm,
        cli_mode=False,  # CLI mode = False will enable browser tools
    )

    # Set up callback collection
    received_events: list = []
    last_event_time = {"ts": time.time()}

    def event_callback(event) -> None:
        event_type = type(event).__name__
        logger.info(f"🔔 Callback received event: {event_type}\n{event}")
        received_events.append(event)
        last_event_time["ts"] = time.time()

    # Create RemoteConversation using the workspace
    conversation = Conversation(
        agent=agent,
        workspace=workspace,
        callbacks=[event_callback],
        visualize=True,
    )
    assert isinstance(conversation, RemoteConversation)

    logger.info(f"\n📋 Conversation ID: {conversation.state.id}")
    logger.info("📝 Sending first message...")
    conversation.send_message(
        "Could you go to https://all-hands.dev/ blog page and summarize main "
        "points of the latest blog?"
    )
    conversation.run()

    # Wait for user confirm to exit
    y = None
    while y != "y":
        y = input(
            "Because you've enabled extra_ports=True in DockerWorkspace, "
            "you can open a browser tab to see the *actual* browser OpenHands "
            "is interacting with via VNC.\n\n"
            "Link: http://localhost:8012/vnc.html?autoconnect=1&resize=remote\n\n"
            "Press 'y' and Enter to exit and terminate the workspace.\n"
            ">> "
        )
