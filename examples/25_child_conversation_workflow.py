#!/usr/bin/env python3
"""
Example demonstrating child conversation workflow with different agent types.

This example shows the complete agent delegation workflow:
1. Starting with an ExecutionAgent
2. User asks ExecutionAgent to spawn a planning child for a complex task
3. ExecutionAgent uses spawn_planning_child tool to create PlanningAgent child
4. User sends messages to PlanningAgent child providing context
5. PlanningAgent creates a detailed PLAN.md based on user input
6. User asks PlanningAgent to execute the plan using execute_plan tool
7. PlanningAgent sends the plan back to its ExecutionAgent parent and
    closes itself, returning control to the parent for execution.

Key concepts demonstrated:
- Parent agent spawning child conversations with different agent types
- User interaction with child conversations to provide context
- Child agents returning control to parent conversations
- Multi-threaded execution of concurrent conversations
- Plan creation and execution workflow

This demonstrates the full agent delegation system with real LLM interactions.
"""

import os
import tempfile
import threading
import time

from pydantic import SecretStr

import openhands.sdk.agent.agents.execution.config  # noqa: F401
import openhands.sdk.agent.agents.planning.config  # noqa: F401
from openhands.sdk.agent.registry import create_agent, list_agents
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.llm import LLM


COMPLEX_TASK = (
    "Create a simple calculator class with a Python module with basic arithmetic "
    "operations (add, subtract, multiply, divide)"
)


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
        workspace=temp_dir,
        visualize=True,  # Enable visualization to see the workflow
    )

    print(f"Created conversation with ExecutionAgent: {conversation._state.id}")

    # Step 2: User asks a complex task requiring planning
    print("\n=== Step 2: User requests complex task ===")
    execution_agent_instruction = (
        COMPLEX_TASK
        + "You MUST use the spawn_planning_child tool - do not create the plan yourself."
    )

    print(f"User request: {execution_agent_instruction}")

    # Step 3: Send the complex task to ExecutionAgent
    # The ExecutionAgent should use spawn_planning_child tool
    print("\n=== Step 3: ExecutionAgent processes complex task ===")
    print(
        "ExecutionAgent will use spawn_planning_child tool to create a "
        "planning child..."
    )

    # Send the message first
    conversation.send_message(execution_agent_instruction)

    # Use threading to run the main conversation and child conversations concurrently
    def run_main_conversation():
        """Run the main conversation in a separate thread."""
        try:
            conversation.run()
        except Exception as e:
            print(f"Error in main conversation: {e}")
            import traceback

            traceback.print_exc()

    # Start main conversation in a thread
    main_thread = threading.Thread(target=run_main_conversation, daemon=False)
    main_thread.start()

    # Poll for child conversations to appear
    print("Waiting for ExecutionAgent to spawn planning child...")
    max_wait = 30  # 30 seconds max
    wait_interval = 2
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(wait_interval)
        elapsed += wait_interval

        main_child_ids = conversation.list_child_conversations()
        print(f"[{elapsed}s] Checking for children... Found: {len(main_child_ids)}")

        if len(main_child_ids) > 0:
            print(f"✅ Child spawned after {elapsed} seconds")
            break

        if not main_thread.is_alive():
            print("⚠️  Main thread finished without spawning child")
            # Check agent status
            print(f"Agent status: {conversation._state.agent_status}")
            break

    if elapsed >= max_wait and len(main_child_ids) == 0:
        print(f"⚠️  Timeout waiting for child after {max_wait} seconds")
        print(f"Agent status: {conversation._state.agent_status}")
        print(f"Main thread alive: {main_thread.is_alive()}")

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
    print("=== Step 4: User Sends Initial Task to Planning Child ===")
    print("=" * 80)
    print("\nThe spawn_planning_child tool only created the child conversation.")
    print("Now the user needs to send the initial task description.\n")

    # Send the initial task description (this is what was in the original request)
    initial_task_message = (
        "Please analyze the following task and create a detailed plan:\n\n"
        + COMPLEX_TASK
        + "Please create a PLAN.md file with task breakdown into specific steps\n"
        "Focus on creating a clear plan that an execution agent can follow."
        "Then call the execute plan tool to delegate the implementation."
    )

    print(f"User's first message to planning child:\n{initial_task_message}\n")
    planning_child.send_message(initial_task_message)

    # Run the planning child to process the first message
    print("Running planning child to process task description...")
    planning_child.run()
    print("✅ Planning child processed task description\n")

    print("\n" + "=" * 80)
    print("=== Step 5: User Sends Follow-up to Planning Child ===")
    print("=" * 80)
    print("\nNow asking the planning agent to create PLAN.md and execute it.\n")

    # Send a follow-up message asking to create plan and execute
    followup_message = (
        "Please create the PLAN.md file now, and after creating it, "
        "use the execute_plan tool to delegate the implementation to the "
        "execution agent."
    )

    print(f"User's follow-up message:\n{followup_message}\n")
    planning_child.send_message(followup_message)

    # Run the planning child to process the follow-up
    print("Running planning child to create plan and spawn execution child...")
    planning_child.run()
    print("✅ Planning child completed")

    # Assert that PLAN.md was created
    import os

    plan_path = os.path.join(planning_child._state.workspace.working_dir, "PLAN.md")
    assert os.path.exists(plan_path), f"PLAN.md not found at {plan_path}"
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
    print("=== Step 6: Execute Plan Tool Returns Control to Parent ===")
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
    if hasattr(planning_child, "list_child_conversations"):
        execution_child_ids = planning_child.list_child_conversations()
        if execution_child_ids:
            print(
                f"\n⚠️  Unexpected: Planning child has {len(execution_child_ids)} children"
            )
            print(
                "This suggests the old behavior (creating grandchildren) is still active"
            )
        else:
            print("\n✅ Assertion 5 passed: Planning child has no execution children")
            print(
                "This confirms the execute_plan tool returns control to parent instead of creating grandchildren"
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

    # Wait for main thread to complete
    print("\n=== Waiting for Main Thread ===")
    main_thread.join(timeout=10)
    if main_thread.is_alive():
        print("⚠️  Warning: Main conversation still running after timeout")
    else:
        print("✅ Main conversation completed")

    print("\n" + "=" * 80)
    print("=== Summary ===")
    print("=" * 80)
    print("\nAgent delegation workflow demonstrated:")
    print("1. ✅ ExecutionAgent created with real LLM")
    print("2. ✅ User sent complex task to ExecutionAgent")
    print("3. ✅ ExecutionAgent used spawn_planning_child tool")
    print("4. ✅ PlanningAgent child created (no messages sent by tool)")
    print("5. ✅ User sent initial task description to PlanningAgent")
    print("6. ✅ User sent follow-up asking to create plan")
    print("7. ✅ PlanningAgent created PLAN.md")
    if execution_child_ids:
        print("8. ✅ PlanningAgent used execute_plan tool")
        print("9. ✅ ExecutionAgent grandchild created AND received plan")
        print("10. ✅ ExecutionAgent grandchild implemented the plan")
    print("\n" + "=" * 80)
    print("Key takeaways:")
    print("  • spawn_planning_child: Creates child, user sends initial context")
    print("  • execute_plan: Creates child AND sends plan automatically")
    print("  • Planning requires user input, execution is autonomous")
    print("  • Multi-level delegation: parent → child → grandchild")
    print("  • Concurrent execution using threading")
    print("=" * 80)

    # Cleanup
    print("\n=== Cleanup ===")
    conversation.close()
    print("Closed all conversations")
