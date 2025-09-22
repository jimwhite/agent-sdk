import asyncio
import os
import subprocess
import time
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import LLM, Message, get_logger
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation


logger = get_logger(__name__)


class ManagedAPIServer:
    """Context manager for subprocess-managed OpenHands API server."""
    
    def __init__(self, port: int = 8000, host: str = "127.0.0.1"):
        self.port = port
        self.host = host
        self.process = None
        self.base_url = f"http://{host}:{port}"
    
    def __enter__(self):
        """Start the API server subprocess."""
        print(f"Starting OpenHands API server on {self.base_url}...")
        
        # Start the server process
        self.process = subprocess.Popen(
            ["python", "-m", "openhands.agent_server.main", "--port", str(self.port), "--host", self.host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
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
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"Server process terminated unexpectedly:\nSTDOUT: {stdout}\nSTDERR: {stderr}")
            
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
            print("API server stopped.")


async def main():
    """Main async function demonstrating RemoteConversation usage."""
    
    # Configure LLM
    api_key = os.getenv("LITELLM_API_KEY")
    assert api_key is not None, "LITELLM_API_KEY environment variable is not set."
    
    llm = LLM(
        model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
    )
    
    # Use managed API server
    with ManagedAPIServer(port=8001) as server:
        # Create RemoteConversation
        conversation = RemoteConversation(
            base_url=server.base_url,
            llm=llm,
            working_dir=Path.cwd(),
            cli_mode=True,  # Disable browser tools for simplicity
        )
        
        print("=" * 80)
        print("Starting conversation with RemoteConversation...")
        print("=" * 80)
        
        # Start the conversation
        await conversation.start()
        
        try:
            # Send first message and run
            print("\n📝 Sending first message...")
            await conversation.send_message(
                Message(
                    role="user",
                    content="Read the current repo and write 3 facts about the project into FACTS.txt."
                )
            )
            
            print("🚀 Running conversation...")
            await conversation.run()
            
            # Wait a bit for completion
            print("⏳ Waiting for task completion...")
            await asyncio.sleep(2)
            
            # Check status
            status = await conversation.get_status()
            print(f"📊 Current status: {status}")
            
            # Send second message and run
            print("\n📝 Sending second message...")
            await conversation.send_message(
                Message(role="user", content="Great! Now delete that file.")
            )
            
            print("🚀 Running conversation again...")
            await conversation.run()
            
            # Wait for completion
            await asyncio.sleep(2)
            
            # Get final status
            final_status = await conversation.get_status()
            print(f"📊 Final status: {final_status}")
            
            # Get conversation history
            print("\n📜 Getting conversation history...")
            events = await conversation.get_events()
            print(f"📈 Total events: {len(events)}")
            
            # Show some recent events
            print("\n🔍 Recent events:")
            for i, event in enumerate(events[-5:]):  # Show last 5 events
                print(f"  {i+1}. {event.__class__.__name__}: {str(event)[:100]}...")
        
        finally:
            # Clean up
            print("\n🧹 Cleaning up conversation...")
            await conversation.close()
    
    print("\n" + "=" * 80)
    print("✅ RemoteConversation example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
