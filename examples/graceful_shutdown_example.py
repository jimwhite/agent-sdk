"""Example demonstrating graceful shutdown handling for multi-threaded agents.

This example shows how to properly handle CTRL+C (SIGINT) and other shutdown signals
when running agent conversations in threads, ensuring clean resource cleanup.
"""

import os
import threading

from pydantic import SecretStr

from openhands.sdk import LLM, Agent
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.tool import ToolSpec, register_tool
from openhands.sdk.utils.signal_handler import (
    GracefulShutdownHandler,
    wait_for_threads_with_shutdown,
)
from openhands.tools.execute_bash import BashTool
from openhands.tools.str_replace_editor import FileEditorTool


def run_agent_conversation(
    conversation: LocalConversation, shutdown_handler: GracefulShutdownHandler
) -> None:
    """Run agent conversation with shutdown handling."""
    try:
        # Register cleanup callback for this conversation
        shutdown_handler.register_cleanup_callback(conversation.shutdown)

        # Run the conversation
        conversation.run()

    except Exception as e:
        print(f"Error in agent conversation: {e}")
    finally:
        print("Agent conversation thread finished")


def main():
    """Main function demonstrating graceful shutdown."""
    # Configure LLM
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        print("LITELLM_API_KEY environment variable is not set.")
        print("Using a mock LLM for demonstration purposes.")
        # For demo purposes, we'll create a simple LLM config
        # In real usage, you'd need a proper API key
        llm = LLM(
            service_id="demo-llm",
            model="gpt-3.5-turbo",  # This won't work without API key
        )
    else:
        llm = LLM(
            service_id="main-llm",
            model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
            base_url="https://llm-proxy.eval.all-hands.dev",
            api_key=SecretStr(api_key),
        )

    # Tools
    register_tool("BashTool", BashTool)
    register_tool("FileEditorTool", FileEditorTool)
    tools = [
        ToolSpec(name="BashTool", params={"working_dir": os.getcwd()}),
        ToolSpec(name="FileEditorTool"),
    ]

    # Create agents and conversations
    alice_agent = Agent(llm=llm, tools=tools)
    bob_agent = Agent(llm=llm, tools=tools)

    alice_conversation = LocalConversation(alice_agent)
    bob_conversation = LocalConversation(bob_agent)

    print("Starting multi-agent demo with graceful shutdown handling...")
    print("Press Ctrl+C to trigger graceful shutdown")

    # Use the graceful shutdown handler
    with GracefulShutdownHandler() as shutdown_handler:
        # Send initial messages
        alice_conversation.send_message(
            "Hello! Please introduce yourself and then wait for further instructions."
        )
        bob_conversation.send_message(
            "Hello! Please introduce yourself and then wait for further instructions."
        )

        # Start agent threads
        alice_thread = threading.Thread(
            target=run_agent_conversation,
            args=(alice_conversation, shutdown_handler),
            name="Alice-Thread",
        )
        bob_thread = threading.Thread(
            target=run_agent_conversation,
            args=(bob_conversation, shutdown_handler),
            name="Bob-Thread",
        )

        alice_thread.start()
        bob_thread.start()

        # Wait for threads to complete or shutdown to be requested
        wait_for_threads_with_shutdown(
            [alice_thread, bob_thread], shutdown_handler, timeout=5.0
        )

        print("All threads have finished or shutdown was requested")

    print("Demo completed successfully!")


if __name__ == "__main__":
    main()
