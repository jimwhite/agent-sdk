#!/usr/bin/env python3
"""
Agent Delegation Example

This example demonstrates the agent delegation feature where a main agent
delegates tasks to sub-agents for parallel processing.

The main agent receives a high-level programming task "Analyze this Python file for quality."
The main agent decomposes the task into two parallel subtasks:
- Sub-agent 1: perform linting (detect style issues or naming problems)
- Sub-agent 2: perform complexity analysis (count functions or measure cyclomatic complexity)

Each sub-agent runs independently and returns its results to the main agent,
which then merges both analyses into a single consolidated report.

Usage:
    python examples/28_agent_delegation.py
"""

import asyncio
import os
import tempfile
from pathlib import Path

from openhands.sdk import Conversation
from openhands.sdk.llm import LLM
from openhands.tools.preset import get_default_agent


# Sample Python file to analyze
SAMPLE_PYTHON_CODE = '''
import os
import sys
from typing import List, Dict

def calculateSum(numbers):
    """Calculate sum of numbers"""
    total = 0
    for num in numbers:
        total += num
    return total

def process_data(data_list: List[Dict], filter_key: str = None):
    """Process a list of dictionaries"""
    results = []
    for item in data_list:
        if filter_key and filter_key not in item:
            continue
        processed_item = {}
        for key, value in item.items():
            if isinstance(value, str):
                processed_item[key] = value.upper()
            elif isinstance(value, (int, float)):
                processed_item[key] = value * 2
            else:
                processed_item[key] = value
        results.append(processed_item)
    return results

class DataProcessor:
    def __init__(self, config_file_path):
        self.config_file_path = config_file_path
        self.data = []
        
    def load_config(self):
        if not os.path.exists(self.config_file_path):
            raise FileNotFoundError(f"Config file not found: {self.config_file_path}")
        # Simulate config loading
        return {"setting1": "value1", "setting2": "value2"}
    
    def process_batch(self, batch_size=100):
        """Process data in batches"""
        for i in range(0, len(self.data), batch_size):
            batch = self.data[i:i+batch_size]
            yield process_data(batch)

def main():
    processor = DataProcessor("/path/to/config.json")
    try:
        config = processor.load_config()
        data = [{"name": "test", "value": 42}, {"name": "example", "value": 3.14}]
        processor.data = data
        
        for batch_result in processor.process_batch():
            print(f"Processed batch: {batch_result}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''


async def main():
    """Main function demonstrating agent delegation."""
    print("🚀 Starting Agent Delegation Example")
    print("=" * 50)
    
    # Create a temporary Python file to analyze
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(SAMPLE_PYTHON_CODE)
        temp_file_path = f.name
    
    try:
        # Initialize LLM and main agent with delegation capabilities
        llm = LLM(model="gpt-4o-mini")
        main_agent = get_default_agent(llm=llm, enable_delegation=True)
        
        # Create conversation with the main agent
        conversation = Conversation(
            agent=main_agent,
            workspace=Path(os.getcwd()),
            visualize=True,
        )
        
        print(f"📁 Created temporary Python file: {temp_file_path}")
        print("🤖 Main agent will delegate analysis tasks to sub-agents")
        print()
        
        # Send the high-level task to the main agent
        task_message = f"""
        Please analyze the Python file at {temp_file_path} for code quality.
        
        I want you to delegate this work to two sub-agents working in parallel:
        1. Sub-agent 1: Perform linting analysis (style issues, naming problems, imports)
        2. Sub-agent 2: Perform complexity analysis (function count, complexity metrics)
        
        After both sub-agents complete their work, merge their analyses into a 
        single consolidated report with recommendations.
        
        Use the delegation tool to spawn sub-agents, wait for their results,
        and then provide a comprehensive analysis.
        """
        
        print("📤 Sending task to main agent:")
        print(f"   {task_message[:100]}...")
        print()
        
        # Send message and wait for completion
        await conversation.send_message_async(task_message)
        
        print("✅ Agent delegation example completed!")
        print("📊 Check the conversation output above for the delegation workflow")
        
    except Exception as e:
        print(f"❌ Error during delegation example: {e}")
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
            print(f"🧹 Cleaned up temporary file: {temp_file_path}")


if __name__ == "__main__":
    print("Agent Delegation Example")
    print("This example demonstrates parallel task delegation between agents")
    print()
    
    # Check for required environment variables
    if not os.getenv("LLM_API_KEY"):
        print("❌ Error: LLM_API_KEY environment variable is required")
        print("   Please set your OpenAI API key:")
        print("   export LLM_API_KEY=your_api_key_here")
        exit(1)
    
    # Run the async main function
    asyncio.run(main())