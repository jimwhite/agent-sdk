"""
Example demonstrating a two-stage workflow with planning and implementation agents.

This example shows how to use a PlanningAgent to analyze a task and create a detailed
implementation plan, followed by a standard Agent that reads the plan and executes it.

The workflow demonstrates:
1. Planning Agent: Analyzes the project and creates a structured plan
2. Implementation Agent: Reads the plan and executes the implementation
"""

import os
import tempfile
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.tools.preset.default import get_default_agent
from openhands.tools.preset.planning import get_planning_agent


logger = get_logger(__name__)

# Configure LLM
api_key = os.getenv("LITELLM_API_KEY")
assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

llm = LLM(
    model="litellm_proxy/anthropic/claude-sonnet-4-5-20250929",
    base_url="https://llm-proxy.eval.all-hands.dev",
    api_key=SecretStr(api_key),
    service_id="agent",
    drop_params=True,
)

# Create a temporary workspace for this example
with tempfile.TemporaryDirectory() as temp_dir:
    workspace = Path(temp_dir)

    # Create a sample project structure for the agents to work with
    (workspace / "src").mkdir()
    (workspace / "tests").mkdir()
    (workspace / "docs").mkdir()

    # Create some sample files
    (workspace / "README.md").write_text("""# Sample Project

This is a sample Python project for demonstrating the planning agent workflow.

## Structure
- src/: Source code
- tests/: Test files
- docs/: Documentation
""")

    (workspace / "src" / "main.py").write_text("""#!/usr/bin/env python3
\"\"\"Main application entry point.\"\"\"

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")

    (workspace / "src" / "utils.py").write_text("""\"\"\"Utility functions.\"\"\"

def helper_function():
    \"\"\"A simple helper function.\"\"\"
    return "Helper result"
""")

    print(f"Created sample project in: {workspace}")
    print("=" * 80)

    # === STAGE 1: PLANNING AGENT ===
    print("STAGE 1: PLANNING AGENT")
    print("=" * 80)

    planning_agent = get_planning_agent(llm=llm)
    planning_messages = []

    def planning_callback(event: Event):
        if isinstance(event, LLMConvertibleEvent):
            planning_messages.append(event.to_llm_message())

    planning_conversation = Conversation(
        agent=planning_agent,
        callbacks=[planning_callback],
        workspace=str(workspace),
    )

    # Give the planning agent a complex task
    task_description = """
    I need you to analyze this project and create a comprehensive plan for adding
    a new feature: a configuration management system. The system should:

    1. Allow loading configuration from JSON and YAML files
    2. Support environment variable overrides
    3. Provide a simple API for accessing configuration values
    4. Include proper error handling and validation
    5. Have comprehensive tests
    6. Be well documented

    Please analyze the current project structure and create a detailed implementation
    plan that another agent can follow to implement this feature.
    """

    print("Sending task to planning agent...")
    planning_conversation.send_message(task_description)
    planning_conversation.run()

    print(f"Planning stage completed. Generated {len(planning_messages)} messages.")

    # Check if plan was created
    plan_file = workspace / "PLAN.md"
    if plan_file.exists():
        print(f"✅ Plan created: {plan_file}")
        print("Plan preview (first 500 characters):")
        print("-" * 40)
        plan_content = plan_file.read_text()
        print(plan_content[:500] + "..." if len(plan_content) > 500 else plan_content)
        print("-" * 40)
    else:
        print("❌ No plan file was created")

    print("\n" + "=" * 80)

    # === STAGE 2: IMPLEMENTATION AGENT ===
    print("STAGE 2: IMPLEMENTATION AGENT")
    print("=" * 80)

    implementation_agent = get_default_agent(llm=llm, cli_mode=True)
    implementation_messages = []

    def implementation_callback(event: Event):
        if isinstance(event, LLMConvertibleEvent):
            implementation_messages.append(event.to_llm_message())

    implementation_conversation = Conversation(
        agent=implementation_agent,
        callbacks=[implementation_callback],
        workspace=str(workspace),
    )

    # Ask the implementation agent to execute the plan
    if plan_file.exists():
        implementation_task = f"""
        Please read the implementation plan in {plan_file.name} and execute it
        step by step.

        The plan was created by a planning agent and contains detailed instructions
        for implementing a configuration management system. Please follow the plan
        carefully and implement all the specified components.

        Start by reading the plan file to understand what needs to be done.
        """

        print("Sending implementation task to standard agent...")
        implementation_conversation.send_message(implementation_task)
        implementation_conversation.run()

        print(
            f"Implementation stage completed. Generated "
            f"{len(implementation_messages)} messages."
        )

        # Show what was created
        print("\nFiles created during implementation:")
        for file_path in workspace.rglob("*"):
            if file_path.is_file() and file_path.name not in ["PLAN.md", "README.md"]:
                relative_path = file_path.relative_to(workspace)
                print(f"  📄 {relative_path}")
    else:
        print("❌ Cannot proceed with implementation - no plan file found")

    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print(f"Planning Agent Messages: {len(planning_messages)}")
    print(f"Implementation Agent Messages: {len(implementation_messages)}")
    print(f"Total Messages: {len(planning_messages) + len(implementation_messages)}")

    if plan_file.exists():
        print(f"✅ Plan file created: {plan_file.name}")
        print("✅ Two-stage workflow completed successfully")
    else:
        print("❌ Workflow incomplete - planning stage failed")

    print("\nWorkspace contents (final state):")
    for item in sorted(workspace.rglob("*")):
        if item.is_file():
            relative_path = item.relative_to(workspace)
            size = item.stat().st_size
            print(f"  📄 {relative_path} ({size} bytes)")
        elif item.is_dir() and item != workspace:
            relative_path = item.relative_to(workspace)
            print(f"  📁 {relative_path}/")

    print(f"\nTemporary workspace will be cleaned up: {workspace}")
