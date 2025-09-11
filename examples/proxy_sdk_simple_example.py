#!/usr/bin/env python3
"""
Example demonstrating the SIMPLIFIED proxy SDK usage.

Key improvement: Instead of implementing separate proxy classes for each SDK class,
we now use a generic automatic translator that works with ANY class!

This maintains the exact same interface as the regular SDK, but with all operations
proxied to a remote OpenHands server through a single generic proxy mechanism.
"""

from pydantic import SecretStr

from openhands.sdk import LLM, Agent, Conversation, Message, TextContent
from openhands.sdk.client import Proxy
from openhands.tools import BashTool, FileEditorTool


def main():
    """Demonstrate simplified proxy SDK usage."""
    try:
        # Create proxy client - same as before
        proxy = Proxy(
            url="http://localhost:9000",  # Your OpenHands server URL
            api_key="your-api-key-here",  # Optional API key
        )

        # Test server connection
        health = proxy.health_check()
        print(f"Server health: {health}")

        # Import proxy versions of SDK classes
        # The magic: ONE generic proxy handles ALL classes automatically!
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

        # Create agent - automatically proxied to remote server
        agent = ProxyAgent(llm=llm, tools=tools)

        # Create conversation - special case using existing conversation API
        conversation = ProxyConversation(agent=agent)  # type: ignore[call-arg]

        # Send a message (this goes to the remote server)
        message = Message(
            role="user",
            content=[
                TextContent(
                    text="Hello! Can you help me create a simple Python script?"
                )
            ],
        )

        response = conversation.send_message(message)
        if response:
            print(f"Response: {response.content[0].text}")
        else:
            print("No response received")

        # Note: Additional methods would be available if implemented on the server
        print("Conversation proxy created and message sent successfully!")

        # The beauty: You can import ANY class and it will work!
        # No need to manually implement proxy classes for each one

        print("\n--- Demonstrating generic proxy capability ---")

        # Example with a custom class:
        class CustomTool:
            def __init__(self, name: str):
                self.name = name

            def execute(self, command: str):
                return f"Executing {command} with {self.name}"

        ProxyCustomTool = proxy.import_(CustomTool)
        custom_tool = ProxyCustomTool(name="MyTool")
        print(f"Created custom tool: {custom_tool.name}")
        # This would automatically proxy method calls to the server if supported!

    except Exception as e:
        print(f"Failed to connect to server: {e}")


if __name__ == "__main__":
    main()
