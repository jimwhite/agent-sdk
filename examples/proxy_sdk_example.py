#!/usr/bin/env python3
"""
Example demonstrating the proxy SDK usage.

This shows how to use the exact same interface as the regular SDK,
but with all operations proxied to a remote OpenHands server.
"""

from pydantic import SecretStr

from openhands.sdk import LLM, Agent, Conversation, Message, TextContent
from openhands.sdk.client import Proxy
from openhands.tools import BashTool, FileEditorTool


def main():
    # Create proxy connection to remote server
    proxy = Proxy(url="http://localhost:9000", api_key="your-master-key-here")

    # Check server health
    try:
        health = proxy.health_check()
        print(f"Server status: {health}")
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        return

    # Import proxy versions of SDK classes
    # These have the EXACT same interface as the original classes
    ProxyAgent = proxy.import_(Agent)
    ProxyLLM = proxy.import_(LLM)
    ProxyConversation = proxy.import_(Conversation)

    # Use the proxy classes exactly like the original SDK
    llm = ProxyLLM(
        model="claude-sonnet-4-20250514",
        api_key=SecretStr("your-anthropic-api-key"),
    )

    # Create tools (these work the same way)
    tools = [
        BashTool.create(working_dir="/tmp"),
        FileEditorTool.create(),
    ]

    # Create agent - this looks identical to regular SDK usage
    agent = ProxyAgent(llm=llm, tools=tools)

    # Create conversation - this creates a remote conversation on the server
    conversation = ProxyConversation(
        agent=agent,
        max_iteration_per_run=100,
        visualize=True,
    )

    print(f"Created remote conversation with ID: {conversation.id}")

    # Send a message - this goes to the remote server
    message = Message(
        role="user",
        content=[
            TextContent(text="Hello! Can you help me create a simple Python script?")
        ],
    )
    conversation.send_message(message)
    print("Message sent to remote conversation")

    # Run the conversation - this executes remotely
    print("Running conversation on remote server...")
    conversation.run()

    # Check the state - this fetches from remote server
    state = conversation.state
    print(f"Conversation finished: {state.agent_finished}")
    print(f"Number of events: {len(state.events)}")

    # Enable confirmation mode
    conversation.set_confirmation_mode(True)
    print("Confirmation mode enabled")

    # Send another message
    message2 = Message(
        role="user",
        content=[TextContent(text="Now create a simple web server in Python")],
    )
    conversation.send_message(message2)

    # Run one step (will wait for confirmation)
    conversation.run()

    # Check if waiting for confirmation
    state = conversation.state
    if state.agent_waiting_for_confirmation:
        print("Agent is waiting for confirmation")

        # You could either approve by running again, or reject:
        # conversation.run()  # This would approve and continue
        # OR
        conversation.reject_pending_actions("I changed my mind")
        print("Rejected pending actions")

    print("Example completed successfully!")


if __name__ == "__main__":
    main()
