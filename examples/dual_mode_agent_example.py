#!/usr/bin/env python3
"""
Example demonstrating the dual-mode agent functionality.

This example shows how to:
1. Create a DualModeAgent with separate LLM configs for planning and execution
2. Start in planning mode for discussion and analysis
3. Switch to execution mode for implementation
4. Use different prompts and tool sets for each mode
"""

import asyncio

from openhands.sdk.agent import DualModeAgent, DualModeAgentConfig
from openhands.sdk.agent.modes import AgentMode
from openhands.sdk.llm import LLM


async def main():
    """Demonstrate dual-mode agent functionality."""

    # Configure different LLMs for planning and execution
    # In planning mode, use a model optimized for reasoning
    planning_llm = LLM(
        model="gpt-4o-mini",  # Good for reasoning and planning
        service_id="planning-llm",
    )

    # In execution mode, use a model optimized for coding
    execution_llm = LLM(
        model="claude-3-5-sonnet-20241022",  # Good for code generation
        service_id="execution-llm",
    )

    # Define tools for each mode
    # Planning mode: Only built-in tools (read-only discussion)
    # Built-in tools (FinishTool, ThinkTool, ModeSwitchTool) are added automatically
    planning_tools = [
        # Add any additional planning-specific tools here
    ]

    # Execution mode: Full tool access for implementation
    execution_tools = [
        # Add execution-specific tools here
        # ToolSpec(name="BashTool", params={"working_dir": "/workspace"}),
        # ToolSpec(name="FileEditorTool"),
    ]

    # Create dual-mode agent configuration
    config = DualModeAgentConfig(
        planning_llm=planning_llm,
        execution_llm=execution_llm,
        planning_tools=planning_tools,
        execution_tools=execution_tools,
        initial_mode=AgentMode.PLANNING,  # Start in planning mode
    )

    # Create the dual-mode agent
    agent = DualModeAgent(dual_mode_config=config)

    print("🤖 Dual-Mode Agent Example")
    print("=" * 50)

    # Show initial state
    print(f"Initial mode: {agent.current_mode}")
    print(f"Current LLM: {agent.llm.model}")
    print(f"Available tools: {[tool.name for tool in agent.tools]}")
    print(f"System prompt: {agent.system_prompt_filename}")
    print()

    # Create a conversation with the agent
    # conversation = Conversation(agent=agent)  # Uncomment for real usage

    # Simulate planning phase
    print("📋 PLANNING PHASE")
    print("-" * 20)
    print("In planning mode, the agent can:")
    print("- Discuss and analyze requirements")
    print("- Create detailed plans")
    print("- Ask clarifying questions")
    print("- Switch to execution mode when ready")
    print()

    # Add a planning message
    planning_message = (
        "Let's plan how to create a simple Python script that reads a CSV file "
        "and generates a summary report. What steps should we take?"
    )
    print(f"User: {planning_message}")
    print()

    # In a real scenario, you would call conversation.send_message() and
    # conversation.run()
    # For this example, we'll simulate the planning response
    print(
        "Agent (Planning Mode): I'll help you plan this CSV analysis script. "
        "Here's my approach:"
    )
    print("1. First, let's understand the CSV structure and requirements")
    print("2. Design the data processing logic")
    print("3. Plan the summary report format")
    print(
        "4. Once we have a clear plan, I can switch to execution mode to implement it"
    )
    print()

    # Simulate mode switch
    print("🔄 SWITCHING TO EXECUTION MODE")
    print("-" * 30)

    # Switch to execution mode
    observation = agent.switch_mode(AgentMode.EXECUTION)
    print(f"Mode switch result: {observation.success}")
    print(f"Previous mode: {observation.previous_mode}")
    print(f"New mode: {observation.new_mode}")
    print()

    # Show updated state
    print("📝 EXECUTION PHASE")
    print("-" * 18)
    print(f"Current mode: {agent.current_mode}")
    print(f"Current LLM: {agent.llm.model}")
    print(f"Available tools: {[tool.name for tool in agent.tools]}")
    print(f"System prompt: {agent.system_prompt_filename}")
    print()

    print("In execution mode, the agent can:")
    print("- Execute code and commands")
    print("- Create and edit files")
    print("- Run tests and validate results")
    print("- Switch back to planning mode if needed")
    print()

    # Add an execution message
    execution_message = "Now implement the CSV analysis script we planned."
    print(f"User: {execution_message}")
    print()

    # In a real scenario, you would call conversation.send_message() and
    # conversation.run()
    print(
        "Agent (Execution Mode): I'll now implement the CSV analysis script "
        "based on our plan."
    )
    print(
        "I have access to file editing and bash tools to create and test "
        "the implementation."
    )
    print()

    # Demonstrate switching back to planning
    print("🔄 SWITCHING BACK TO PLANNING MODE")
    print("-" * 35)

    observation = agent.switch_mode(AgentMode.PLANNING)
    print(f"Mode switch result: {observation.success}")
    print(f"New mode: {agent.current_mode}")
    print()

    print("✅ Example completed!")
    print("This demonstrates how the dual-mode agent can:")
    print("- Use different LLMs for planning vs execution")
    print("- Restrict tools in planning mode for read-only discussion")
    print("- Provide full tool access in execution mode")
    print("- Switch between modes seamlessly")
    print("- Use different system prompts for each mode")


if __name__ == "__main__":
    asyncio.run(main())
