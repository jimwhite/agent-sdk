import asyncio
import os
import subprocess
import time
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import LLM, Message, get_logger
from openhands.sdk.conversation.impl.remote_conversation import RemoteConversation
from openhands.sdk.preset.default import get_default_agent


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
            ["python", "-m", "openhands.agent_server", "--port", str(self.port), "--host", self.host, "--no-reload"],
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
        # Create agent
        agent = get_default_agent(
            llm=llm,
            working_dir=Path.cwd(),
            cli_mode=True,  # Disable browser tools for simplicity
        )
        
        # Create RemoteConversation
        conversation = RemoteConversation(
            agent=agent,
            host=server.base_url,
        )
        
        print("=" * 80)
        print("Starting conversation with RemoteConversation...")
        print("=" * 80)
        
        try:
            # Send first message and run
            print("\n📝 Sending first message...")
            conversation.send_message(
                "Read the current repo and write 3 facts about the project into FACTS.txt."
            )
            
            print("🚀 Running conversation...")
            conversation.run()
            
            print("✅ First task completed!")
            
            # Wait a bit to ensure the first task is fully finished
            print("⏳ Waiting for first task to fully complete...")
            await asyncio.sleep(3)
            
            # Send second message and run
            print("\n📝 Sending second message...")
            conversation.send_message("Great! Now delete that file.")
            
            print("🚀 Running conversation again...")
            conversation.run()
            
            print("✅ Second task completed!")
            
            print(f"\n📋 Conversation ID: {conversation.id}")
        
        finally:
            # Clean up
            print("\n🧹 Cleaning up conversation...")
            conversation.close()
    
    print("\n" + "=" * 80)
    print("✅ RemoteConversation example completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())