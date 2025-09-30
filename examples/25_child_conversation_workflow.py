"""
Child Conversation Workflow Example

This example demonstrates an extensible agent system with a hierarchical
workflow:
ExecutionAgent → PlanningAgent → ExecutionAgent

The workflow showcases:
1. Parent ExecutionAgent receives a task
2. Creates a PlanningAgent child conversation to research and plan
3. PlanningAgent creates its own ExecutionAgent child to implement the plan
4. Results flow back through the conversation hierarchy

This pattern enables complex multi-agent workflows with clear separation of
concerns.
"""

import os

from openhands.sdk import LLM, Conversation
from openhands.tools.preset.default import get_execution_agent


def main():
    """Demonstrate the child conversation workflow."""

    # Configure LLM
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        print("❌ Error: LITELLM_API_KEY environment variable is required")
        print("   Set it with: export LITELLM_API_KEY='your-api-key'")
        return

    from pydantic import SecretStr

    llm = LLM(
        model="anthropic/claude-3-5-sonnet-20241022",
        api_key=SecretStr(api_key) if api_key else None,
        service_id="litellm",
    )

    # Create main conversation with ExecutionAgent
    execution_agent = get_execution_agent(llm)

    # Create working directory
    import tempfile

    working_dir = tempfile.mkdtemp(prefix="child_conversation_demo_")

    conversation = Conversation(agent=execution_agent, working_dir=working_dir)

    print("🚀 CHILD CONVERSATION WORKFLOW DEMO")
    print("=" * 80)
    print()
    print("This example demonstrates a hierarchical agent workflow:")
    print("1. 🤖 ExecutionAgent (parent) receives the task")
    print("2. 📋 Creates PlanningAgent child to research and plan")
    print("3. ⚙️  PlanningAgent creates ExecutionAgent child to implement")
    print("4. ✅ Results flow back through the conversation hierarchy")
    print()

    # Define the task
    task = """Create a simple Flask web application with the following
features:
1. A home page that displays "Hello, World!"
2. An about page with some basic information
3. A contact form that accepts name and email
4. Basic CSS styling to make it look professional
5. Proper project structure with templates and static files

Please research Flask best practices and create a comprehensive plan before
implementation."""

    print(f"📝 Task: {task}")
    print()

    # Add initial message to start the workflow
    conversation.send_message(
        f"""I need you to create a Flask web application. Here's what I want
you to do:

{task}

Please follow this workflow:

1. First, create a child conversation with a PlanningAgent to research Flask
   best practices and create a detailed implementation plan. Save the plan as
   PLAN.md.

2. After the planning is complete, create another child conversation with an
   ExecutionAgent to implement the plan.

This demonstrates a hierarchical workflow where:
- You (ExecutionAgent) coordinate the overall process
- A PlanningAgent child handles research and planning
- An ExecutionAgent child handles implementation

Start by creating the PlanningAgent child conversation for research and
planning."""
    )

    print("🤖 ExecutionAgent is processing the task...")
    print("   This may take a few minutes as it involves:")
    print("   - Creating a PlanningAgent child conversation")
    print("   - Planning agent researching and writing PLAN.md")
    print("   - Creating an ExecutionAgent child for implementation")
    print("   - Implementation of the Flask web application")
    print()

    # Run the conversation
    conversation.run()

    print("\n" + "=" * 80)
    print("✅ WORKFLOW COMPLETED")
    print("=" * 80)
    print()

    # Show the results
    print("📂 Check the working directory for:")
    print("   - PLAN.md (research and planning document)")
    print("   - Flask application files and directories")
    print("   - All implemented components")
    print()
    print(f"📁 Working directory: {working_dir}")


if __name__ == "__main__":
    main()
