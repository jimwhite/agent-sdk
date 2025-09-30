#!/usr/bin/env python3
"""
Demo script showing how to use the ACP authenticate method to configure LLM settings.

This script demonstrates:
1. Initializing the ACP connection
2. Authenticating with LLM configuration
3. Creating a session with the configured LLM
4. Sending a prompt to test the configuration

Usage:
    python examples/acp_authenticate_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the path so we can import openhands modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from acp import InitializeRequest, NewSessionRequest, PromptRequest
from acp.schema import AuthenticateRequest, ClientCapabilities, ContentBlock1


async def demo_authenticate():
    """Demonstrate ACP authentication with LLM configuration."""
    print("🚀 ACP Authentication Demo")
    print("=" * 50)
    
    # Import here to avoid issues if not in the right environment
    from openhands.agent_server.acp.server import OpenHandsACPAgent
    from unittest.mock import AsyncMock, MagicMock
    import tempfile
    
    # Create a mock connection
    mock_conn = MagicMock()
    mock_conn.sessionUpdate = AsyncMock()
    
    # Create temporary persistence directory
    with tempfile.TemporaryDirectory() as temp_dir:
        persistence_dir = Path(temp_dir)
        
        # Create the ACP agent
        agent = OpenHandsACPAgent(mock_conn, persistence_dir)
        
        print("1️⃣ Initializing ACP connection...")
        
        # Initialize the connection
        init_request = InitializeRequest(
            protocolVersion=1,
            clientCapabilities=ClientCapabilities(),
        )
        
        init_response = await agent.initialize(init_request)
        print(f"   ✅ Protocol version: {init_response.protocolVersion}")
        print(f"   ✅ Available auth methods: {[method.id for method in init_response.authMethods or []]}")
        
        print("\n2️⃣ Authenticating with LLM configuration...")
        
        # Configure LLM settings
        llm_config = {
            "model": "gpt-4o-mini",
            "api_key": "your-api-key-here",
            "base_url": "https://api.openai.com/v1",
            "temperature": 0.7,
            "max_output_tokens": 2000,
            "timeout": 30,
        }
        
        # Authenticate with LLM configuration
        auth_request = AuthenticateRequest(
            methodId="llm_config",
            **{"_meta": llm_config}
        )
        
        auth_response = await agent.authenticate(auth_request)
        if auth_response:
            print("   ✅ Authentication successful!")
            print(f"   ✅ Configured parameters: {list(llm_config.keys())}")
        else:
            print("   ❌ Authentication failed!")
            return
        
        print("\n3️⃣ Creating session with configured LLM...")
        
        # Create a new session
        session_request = NewSessionRequest(
            cwd=str(Path.cwd()),
            mcpServers=[]
        )
        
        session_response = await agent.newSession(session_request)
        session_id = session_response.sessionId
        print(f"   ✅ Session created: {session_id}")
        
        print("\n4️⃣ Testing LLM configuration...")
        
        # Send a test prompt
        prompt_request = PromptRequest(
            sessionId=session_id,
            prompt=[
                ContentBlock1(
                    type="text",
                    text="Hello! Can you tell me what LLM model you are using?"
                )
            ]
        )
        
        try:
            prompt_response = await agent.prompt(prompt_request)
            print(f"   ✅ Prompt sent successfully!")
            print(f"   ✅ Response ID: {prompt_response.responseId}")
        except Exception as e:
            print(f"   ⚠️  Prompt failed (expected without real API key): {e}")
        
        print("\n🎉 Demo completed!")
        print("\nKey features demonstrated:")
        print("• ACP protocol initialization with auth method advertisement")
        print("• LLM configuration via authenticate method")
        print("• Parameter validation and storage")
        print("• Session creation with configured LLM")
        print("• Integration with OpenHands agent system")
        
        print(f"\n📋 Configured LLM parameters:")
        for key, value in llm_config.items():
            if key == "api_key":
                value = "***hidden***"
            print(f"   • {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo_authenticate())