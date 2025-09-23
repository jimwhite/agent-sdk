import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import LLM, Conversation, get_logger
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.sdk.preset.default import get_default_agent


logger = get_logger(__name__)


def _stream_output(stream, prefix, target_stream):
    """Stream output from subprocess to target stream with prefix."""
    try:
        for line in iter(stream.readline, ""):
            if line:
                target_stream.write(f"[{prefix}] {line}")
                target_stream.flush()
    except Exception as e:
        print(f"Error streaming {prefix}: {e}", file=sys.stderr)
    finally:
        stream.close()


class ManagedAPIServer:
    """Context manager for subprocess-managed OpenHands API server."""

    def __init__(self, port: int = 8000, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.process = None
        self.base_url = f"http://{host}:{port}"
        self.stdout_thread = None
        self.stderr_thread = None

    def __enter__(self):
        """Start the API server subprocess."""
        print(f"Starting OpenHands API server on {self.base_url}...")

        # Start the server process
        self.process = subprocess.Popen(
            [
                "python",
                "-m",
                "openhands.agent_server",
                "--port",
                str(self.port),
                "--host",
                self.host,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={"LOG_JSON": "true", **os.environ},
        )

        # Start threads to stream stdout and stderr
        self.stdout_thread = threading.Thread(
            target=_stream_output,
            args=(self.process.stdout, "SERVER", sys.stdout),
            daemon=True,
        )
        self.stderr_thread = threading.Thread(
            target=_stream_output,
            args=(self.process.stderr, "SERVER", sys.stderr),
            daemon=True,
        )

        self.stdout_thread.start()
        self.stderr_thread.start()

        # Wait for server to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                import httpx

                response = httpx.get(f"{self.base_url}/health", timeout=1.0)
                if response.status_code == 200:
                    print(f"API server is ready at {self.base_url}")
                    return self
            except Exception:
                pass

            if self.process.poll() is not None:
                # Process has terminated
                raise RuntimeError(
                    "Server process terminated unexpectedly. "
                    "Check the server logs above for details."
                )

            time.sleep(1)

        raise RuntimeError(f"Server failed to start after {max_retries} seconds")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the API server subprocess."""
        if self.process:
            print("Stopping API server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Force killing API server...")
                self.process.kill()
                self.process.wait()

            # Wait for streaming threads to finish (they're daemon threads,
            # so they'll stop automatically)
            # But give them a moment to flush any remaining output
            time.sleep(0.5)
            print("API server stopped.")


if __name__ == "__main__":
    api_key = os.getenv("LITELLM_API_KEY")
    assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

    llm = LLM(
        model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )

    # Use managed API server
    with ManagedAPIServer(port=8001) as server:
        # Create agent
        agent = get_default_agent(
            llm=llm,
            working_dir=str(Path.cwd()),
            cli_mode=True,  # Disable browser tools for simplicity
        )

        # Define callbacks to test the WebSocket functionality
        received_events = []
        event_tracker = {"last_event_time": time.time()}

        def event_callback(event):
            """Callback to capture events for testing."""
            event_type = type(event).__name__
            print(f"🔔 Callback received event: {event_type}\n{event}")
            received_events.append(event)
            event_tracker["last_event_time"] = time.time()

        # Create RemoteConversation with callbacks
        conversation = Conversation(
            agent=agent,
            host=server.base_url,
            callbacks=[event_callback],
        )
        assert isinstance(conversation, RemoteConversation)

        print("=" * 80)
        print("Starting conversation with RemoteConversation...")
        print("=" * 80)

        try:
            # Send first message and run
            print("\n📝 Sending first message...")
            conversation.send_message(
                "Read the current repo and write 3 facts about "
                "the project into FACTS.txt."
            )

            print("🚀 Running conversation...")
            conversation.run()

            print("✅ First task completed!")
            print(f"Agent status: {conversation.state.agent_status}")

            # Wait for events to stop coming (no events for 2 seconds)
            print("⏳ Waiting for events to stop...")
            while time.time() - event_tracker["last_event_time"] < 2.0:
                time.sleep(0.1)
            print("✅ Events have stopped")

            # Send second message and run
            print("\n📝 Sending second message...")
            conversation.send_message("Great! Now delete that file.")

            print("🚀 Running conversation again...")
            # Retry logic for 409 conflicts
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    conversation.run()
                    break
                except Exception as e:
                    if "409" in str(e) and attempt < max_retries - 1:
                        print(
                            f"⏳ Conversation still running, waiting... "
                            f"(attempt {attempt + 1})"
                        )
                        time.sleep(1)
                        continue
                    raise

            print("✅ Second task completed!")

            print(f"\n📋 Conversation ID: {conversation.state.id}")

            # Demonstrate state.events functionality
            print("\n" + "=" * 50)
            print("📊 Demonstrating State Events API")
            print("=" * 50)

            # Count total events using state.events
            total_events = len(conversation.state.events)
            print(f"📈 Total events in conversation: {total_events}")

            # Get recent events (last 5) using state.events
            print("\n🔍 Getting last 5 events using state.events...")
            all_events = conversation.state.events
            recent_events = all_events[-5:] if len(all_events) >= 5 else all_events

            for i, event in enumerate(recent_events, 1):
                event_type = type(event).__name__
                timestamp = getattr(event, "timestamp", "Unknown")
                print(f"  {i}. {event_type} at {timestamp}")

            # Let's see what the actual event types are
            print("\n🔍 Event types found:")
            event_types = set()
            for event in recent_events:
                event_type = type(event).__name__
                event_types.add(event_type)
            for event_type in sorted(event_types):
                print(f"  - {event_type}")

            # Filter message events from state.events
            print("\n💬 Finding message events in state.events...")
            message_events = []
            for event in conversation.state.events:
                if hasattr(event, "llm_message") or "Message" in type(event).__name__:
                    message_events.append(event)

            print(f"📝 Found {len(message_events)} message-related events:")
            for i, event in enumerate(message_events[:2], 1):  # Show first 2
                event_type = type(event).__name__

                # Try to extract message content
                content = "No content available"
                if hasattr(event, "llm_message") and event.llm_message:
                    llm_message = event.llm_message

                    # Get content from the message
                    if hasattr(llm_message, "content") and llm_message.content:
                        content_list = llm_message.content
                        if isinstance(content_list, list) and len(content_list) > 0:
                            first_content = content_list[0]
                            if hasattr(first_content, "text"):
                                content = first_content.text
                            elif isinstance(first_content, dict):
                                content = first_content.get("text", "No text content")
                            else:
                                content = str(first_content)
                elif hasattr(event, "content"):
                    content = str(event.content)

                # Truncate long content
                if len(content) > 100:
                    content = content[:100] + "..."

                timestamp = getattr(event, "timestamp", "Unknown")
                print(f"  {i}. [{event_type}] {content} at {timestamp}")

            # Show callback results
            print("\n" + "=" * 50)
            print("📡 WebSocket Callback Results")
            print("=" * 50)
            print(f"📊 Total events received via callbacks: {len(received_events)}")

            if received_events:
                print("\n🔍 Event types received via callbacks:")
                callback_event_types = set()
                for event in received_events:
                    event_type = type(event).__name__
                    callback_event_types.add(event_type)
                for event_type in sorted(callback_event_types):
                    count = sum(
                        1 for e in received_events if type(e).__name__ == event_type
                    )
                    print(f"  - {event_type}: {count}")
            else:
                print("⚠️  No events received via callbacks")

        finally:
            # Clean up
            print("\n🧹 Cleaning up conversation...")
            conversation.close()
