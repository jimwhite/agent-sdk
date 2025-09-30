#!/usr/bin/env python3
"""
Example demonstrating child conversation workflow with different agent types.

This example shows the complete agent delegation workflow:
1. Starting with an ExecutionAgent
2. User asks a complex task requiring planning
3. ExecutionAgent uses spawn_planning_child tool to create PlanningAgent child
4. PlanningAgent analyzes the task and creates PLAN.md
5. PlanningAgent uses execute_plan tool to spawn ExecutionAgent child
6. ExecutionAgent child implements the plan step by step

This demonstrates the full agent delegation system with real LLM interactions.
"""

import os
import tempfile

from pydantic import SecretStr

from openhands.sdk.agent.registry import create_agent, list_agents
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.llm import LLM


def main():
    """Demonstrate the child conversation workflow."""

    # Configure LLM (same pattern as other examples)
    api_key = os.getenv("LITELLM_API_KEY")
    assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

    llm = LLM(
        model="litellm_proxy/anthropic/claude-sonnet-4-5-20250929",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
        service_id="agent",
        drop_params=True,
    )

    # Create temporary working directory
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Working directory: {temp_dir}")

        # List available agents
        print("\nAvailable agents:")
        agents = list_agents()
        for name, description in agents.items():
            print(f"  {name}: {description}")

        # Step 1: Start with an ExecutionAgent
        print("\n=== Step 1: Creating ExecutionAgent ===")
        execution_agent = create_agent("execution", llm, enable_browser=False)

        conversation = LocalConversation(
            agent=execution_agent,
            working_dir=temp_dir,
            visualize=True,  # Enable visualization to see the workflow
        )

        print(f"Created conversation with ExecutionAgent: {conversation._state.id}")

        # Step 2: User asks a complex task requiring planning
        print("\n=== Step 2: User requests complex task ===")
        complex_task = (
            "I need to build a simple web application with the following "
            "requirements:\n"
            "1. A Python Flask backend with REST API endpoints\n"
            "2. A simple HTML frontend with JavaScript\n"
            "3. Database integration using SQLite\n"
            "4. User authentication system\n"
            "5. Proper project structure and documentation\n\n"
            "This is complex - please create a detailed plan first using the "
            "spawn_planning_child tool, then execute the plan."
        )

        print(f"User request: {complex_task}")

        # Step 3: Send the complex task to ExecutionAgent
        # The ExecutionAgent should use spawn_planning_child tool
        print("\n=== Step 3: ExecutionAgent processes complex task ===")
        print(
            "ExecutionAgent will use spawn_planning_child tool to create a "
            "planning child..."
        )

        conversation.send_message(complex_task)
        conversation.run()

        print("✅ ExecutionAgent has processed the task and should have:")
        print("   - Used spawn_planning_child tool to create a PlanningAgent child")
        print("   - PlanningAgent analyzed the task and created PLAN.md")
        print(
            "   - PlanningAgent used execute_plan tool to create ExecutionAgent child"
        )
        print("   - ExecutionAgent child began implementing the plan")

        # Show child conversations hierarchy
        print("\n=== Child Conversations Hierarchy ===")
        main_child_ids = conversation.list_child_conversations()
        print(f"Main conversation children: {main_child_ids}")

        for child_id in main_child_ids:
            child = conversation.get_child_conversation(child_id)
            if child:
                print(
                    f"  {child_id}: {child.agent.__class__.__name__} in "
                    f"{child._state.working_dir}"
                )

                # Check if this child has its own children
                if hasattr(child, "list_child_conversations"):
                    grandchild_ids = child.list_child_conversations()
                    if grandchild_ids:
                        print(f"    └─ Children: {grandchild_ids}")
                        for grandchild_id in grandchild_ids:
                            grandchild = child.get_child_conversation(grandchild_id)
                            if grandchild:
                                print(
                                    f"      {grandchild_id}: "
                                    f"{grandchild.agent.__class__.__name__} in "
                                    f"{grandchild._state.working_dir}"
                                )

        print("\n=== Summary ===")
        print("Agent delegation workflow demonstrated:")
        print("1. ✅ ExecutionAgent created with real LLM")
        print("2. ✅ Complex task sent to ExecutionAgent")
        print("3. ✅ ExecutionAgent used spawn_planning_child tool")
        print("4. ✅ PlanningAgent child created and analyzed task")
        print("5. ✅ PlanningAgent created PLAN.md")
        print("6. ✅ PlanningAgent used execute_plan tool")
        print("7. ✅ ExecutionAgent child created to implement plan")
        print("\nThis demonstrates the complete agent delegation system!")

        # Cleanup
        print("\n=== Cleanup ===")
        conversation.close()
        print("Closed all conversations")


if __name__ == "__main__":
    # Import agent configurations to trigger auto-registration
    import openhands.sdk.agent.agents.execution.config  # noqa: F401
    import openhands.sdk.agent.agents.planning.config  # noqa: F401

    main()
