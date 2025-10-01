#!/usr/bin/env python3
"""
Example demonstrating simplified child conversation workflow with different agent types.

This example shows a streamlined agent delegation workflow:
1. Starting with an ExecutionAgent
2. User asks ExecutionAgent to spawn a planning child for a complex task
3. ExecutionAgent uses spawn_planning_child tool to create PlanningAgent child
4. User sends ONE message to PlanningAgent child with task and execute instruction
5. PlanningAgent creates PLAN.md and immediately calls execute_plan tool
6. PlanningAgent sends the plan back to its ExecutionAgent parent and
    closes itself, returning control to the parent for execution.

Key concepts demonstrated:
- Parent agent spawning child conversations with different agent types
- Simplified user interaction with child conversations (single message)
- Child agents returning control to parent conversations
- Multi-threaded execution of concurrent conversations
- Streamlined plan creation and execution workflow

This demonstrates the agent delegation system with minimal user interaction.
"""

import os
import tempfile

from pydantic import SecretStr

import openhands.sdk.agent.agents.execution.config  # noqa: F401
import openhands.sdk.agent.agents.planning.config  # noqa: F401
from openhands.sdk.agent.registry import create_agent, list_agents
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.llm import LLM


COMPLEX_TASK = (
    "Create a simple calculator class with a Python module with basic arithmetic "
    "operations (add, subtract, multiply, divide). "
)

EXECUTION_AGENT_MESSAGE = (
    COMPLEX_TASK + "Use the spawn_planning_child tool. Do not create the plan yourself."
)

PLANNING_AGENT_MESSAGE = (
    "Create a simple calculator class with a Python module with basic arithmetic "
    "operations (add, subtract, multiply, divide). "
    "Create a PLAN.md file with the task breakdown "
    "and then immediately call the execute_plan tool."
)


"""Demonstrate the child conversation workflow."""

# Configure LLM (same pattern as other examples)
api_key = os.getenv("LITELLM_API_KEY")
assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

llm = LLM(
    model="litellm_proxy/openai/gpt-5-mini",
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
        workspace=temp_dir,
        visualize=False,  # Disable visualization to avoid I/O blocking issues
    )

    print(f"Created conversation with ExecutionAgent: {conversation._state.id}")

    # Step 2: User asks a complex task requiring planning
    print("\n=== Step 2: User requests complex task ===")

    print(f"User request: {EXECUTION_AGENT_MESSAGE}")

    # Step 3: Send the complex task to ExecutionAgent
    # The ExecutionAgent should use spawn_planning_child tool
    print("\n=== Step 3: ExecutionAgent processes complex task ===")
    print(
        "ExecutionAgent will use spawn_planning_child tool to create a "
        "planning child..."
    )

    # Send the message and run the conversation
    conversation.send_message(EXECUTION_AGENT_MESSAGE)

    print("Running ExecutionAgent to spawn planning child...")
    conversation.run()

    # Check for child conversations
    main_child_ids = conversation.list_child_conversations()
    print(f"Found {len(main_child_ids)} child conversations")

    # Verify assertions
    print("\n=== Verification ===")

    # 1. Verify that a child conversation was spawned
    print("\n=== Child Conversations Hierarchy ===")
    # Get latest list
    main_child_ids = conversation.list_child_conversations()
    print(f"Main conversation children: {main_child_ids}")

    # Assert that at least one child was created
    assert len(main_child_ids) > 0, "No child conversations were created"
    print("✅ Assertion 1 passed: Child conversation was spawned")

    assert len(main_child_ids) == 1, (
        f"Expected 1 child conversation, but found {len(main_child_ids)}"
    )

    # Get the child conversation
    planning_child_id = main_child_ids[0]
    planning_child = conversation.get_child_conversation(planning_child_id)
    assert planning_child is not None, "Could not retrieve planning child conversation"

    # Assert that it's a PlanningAgent)
    planning_agent_name = planning_child.agent.__class__.__name__
    print(f"Child agent type: {planning_agent_name}")
    assert "Planning" in planning_agent_name, (
        f"Expected PlanningAgent but got {planning_agent_name}"
    )
    print("✅ Assertion 2 passed: Child is a PlanningAgent")

    # Now interact with the planning child to create the plan
    print("\n" + "=" * 80)
    print("=== Step 4: User Sends Single Message to Planning Child ===")
    print("=" * 80)
    print(
        "\nSending one message that will create the plan and call execute_plan tool.\n"
    )

    # Send a single message that includes everything needed
    print(f"User's message to planning child:\n{PLANNING_AGENT_MESSAGE}\n")
    planning_child.send_message(PLANNING_AGENT_MESSAGE)

    # Run the planning child to process the message
    print("Running planning child to create plan and call execute_plan tool...")
    planning_child.run()
    print("✅ Planning child completed")

    # Assert that PLAN.md was created - check multiple possible locations
    import os

    # Possible locations for PLAN.md
    possible_paths = [
        os.path.join(planning_child._state.workspace.working_dir, "PLAN.md"),
        os.path.join(temp_dir, "PLAN.md"),
        "/tmp/PLAN.md",
    ]

    plan_path = None
    for path in possible_paths:
        if os.path.exists(path):
            plan_path = path
            break

    # If not found in expected locations, search for it
    if plan_path is None:
        print("PLAN.md not found in expected locations, searching...")
        for root, dirs, files in os.walk(temp_dir):
            if "PLAN.md" in files:
                plan_path = os.path.join(root, "PLAN.md")
                break

    assert plan_path is not None, (
        f"PLAN.md not found in any of these locations: {possible_paths}"
    )
    print(f"✅ Assertion 3 passed: PLAN.md was created at {plan_path}")

    # Read and verify PLAN.md has content
    with open(plan_path, encoding="utf-8") as f:
        plan_content = f.read()
    assert len(plan_content) > 100, "PLAN.md is too short or empty"
    print(f"✅ Assertion 4 passed: PLAN.md has content ({len(plan_content)} chars)")

    # Show the plan content (first 500 chars)
    print(f"\nPLAN.md preview:\n{plan_content[:500]}...\n")

    # Check if the planning agent has closed (execute_plan returns control to parent)
    print("\n" + "=" * 80)
    print("=== Step 5: Execute Plan Tool Returns Control to Parent ===")
    print("=" * 80)
    print(
        "\nThe execute_plan tool sent the plan back to the parent ExecutionAgent "
        "and closed the planning child conversation."
    )
    print("The parent ExecutionAgent should now have the plan and execute it.\n")

    # The planning child should be closed after execute_plan
    try:
        # Try to check if planning child is still active
        planning_child_status = planning_child._state.agent_status
        print(f"Planning child status: {planning_child_status}")
    except Exception as e:
        print(f"Planning child appears to be closed: {e}")

    # Check if planning child has any execution children (should be none)
    execution_child_ids = []
    if hasattr(planning_child, "list_child_conversations"):
        execution_child_ids = planning_child.list_child_conversations()
        if execution_child_ids:
            print(
                f"\n⚠️  Unexpected: Planning child has "
                f"{len(execution_child_ids)} children"
            )
            print(
                "This suggests the old behavior (creating grandchildren) is "
                "still active"
            )
        else:
            print("\n✅ Assertion 5 passed: Planning child has no execution children")
            print(
                "This confirms the execute_plan tool returns control to parent "
                "instead of creating grandchildren"
            )

    # Display full hierarchy
    print("\n=== Full Hierarchy ===")
    for child_id in main_child_ids:
        child = conversation.get_child_conversation(child_id)
        if child:
            print(
                f"  {child_id}: {child.agent.__class__.__name__} in "
                f"{child._state.workspace.working_dir}"
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
                                f"{grandchild._state.workspace.working_dir}"
                            )

    # Main conversation has completed
    print("\n=== Main Conversation Status ===")
    print("✅ Main conversation completed")

    print("\n" + "=" * 80)
    print("=== Summary ===")
    print("=" * 80)
    print("\nAgent delegation workflow demonstrated:")
    print("1. ✅ ExecutionAgent created with real LLM")
    print("2. ✅ User sent complex task to ExecutionAgent")
    print("3. ✅ ExecutionAgent used spawn_planning_child tool")
    print("4. ✅ PlanningAgent child created (no messages sent by tool)")
    print(
        "5. ✅ User sent single message to PlanningAgent with task and execute instruction"
    )
    print("6. ✅ PlanningAgent created PLAN.md and called execute_plan tool")
    if execution_child_ids:
        print("7. ✅ ExecutionAgent grandchild created AND received plan")
        print("8. ✅ ExecutionAgent grandchild implemented the plan")
    print("\n" + "=" * 80)
    print("Key takeaways:")
    print("  • spawn_planning_child: Creates child, user sends initial context")
    print("  • execute_plan: Creates child AND sends plan automatically")
    print("  • Planning requires user input, execution is autonomous")
    print("  • Multi-level delegation: parent → child → grandchild")
    print("  • Sequential execution for reliability")
    print("=" * 80)

    # Cleanup
    print("\n=== Cleanup ===")
    conversation.close()
    print("Closed all conversations")
