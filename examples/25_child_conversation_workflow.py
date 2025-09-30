#!/usr/bin/env python3
"""
Example demonstrating child conversation workflow with different agent types.

This example shows:
1. Starting with an ExecutionAgent
2. User asks a complex task requiring planning
3. Agent creates a PlanningAgent child conversation
4. PlanningAgent researches and writes PLAN.md
5. Create "execute_plan" tool that reads PLAN.md and spawns ExecutionAgent child
6. ExecutionAgent implements the plan
"""

import tempfile
from pathlib import Path

from openhands.sdk.agent.registry import create_agent, list_agents
from openhands.sdk.conversation.impl.local_conversation import LocalConversation
from openhands.sdk.llm import LLM


def main():
    """Demonstrate the child conversation workflow."""

    # Initialize LLM (using a mock for this example)

    llm = LLM(model="mock", service_id="mock")  # Use mock LLM for demonstration

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
            visualize=False,  # Reduce noise in example
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
            "This is complex - please create a detailed plan first before implementing."
        )

        print(f"User request: {complex_task[:100]}...")

        # Step 3: Manually create planning child (simulating the spawn tool)
        print("\n=== Step 3: Creating planning child conversation ===")

        # Create a planning agent
        from openhands.sdk.agent.registry import AgentRegistry

        registry = AgentRegistry()
        planning_agent = registry.create("planning", llm=llm)

        # Create child conversation
        planning_child = conversation.create_child_conversation(
            agent=planning_agent,
            visualize=False,
        )

        # Send initial message to planning child
        initial_message = (
            f"Please analyze this task and create a detailed plan:\n\n"
            f"{complex_task}\n\n"
            "Create a PLAN.md file with:\n"
            "1. Task breakdown into specific steps\n"
            "2. Dependencies between steps\n"
            "3. Implementation details\n"
            "4. Risk considerations\n"
            "5. Testing approach"
        )

        planning_child.send_message(initial_message)

        print("✅ Created planning child conversation")
        print(f"Child ID: {planning_child._state.id}")
        print(f"Working Directory: {planning_child._state.working_dir}")

        # Step 4: Simulate PlanningAgent creating PLAN.md
        print("\n=== Step 4: PlanningAgent creates plan ===")
        print("PlanningAgent analyzing request and creating plan...")

        # Create a sample PLAN.md file to demonstrate the workflow
        plan_content = """# Web Application Implementation Plan

## Project Structure
```
webapp/
├── app.py              # Flask application entry point
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── models/
│   ├── __init__.py
│   ├── user.py        # User model
│   └── database.py    # Database setup
├── routes/
│   ├── __init__.py
│   ├── auth.py        # Authentication routes
│   └── api.py         # API endpoints
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── templates/
│   ├── base.html
│   ├── index.html
│   └── login.html
└── tests/
    ├── __init__.py
    └── test_app.py

## Implementation Steps

### Step 1: Project Setup
1. Create project directory structure
2. Create requirements.txt with Flask, SQLAlchemy, Flask-Login
3. Create basic config.py for database and app settings

### Step 2: Database Models
1. Create models/database.py with SQLAlchemy setup
2. Create models/user.py with User model
3. Initialize database tables

### Step 3: Authentication System
1. Create routes/auth.py with login/logout/register routes
2. Implement password hashing and session management
3. Create login and registration templates

### Step 4: API Endpoints
1. Create routes/api.py with REST endpoints
2. Implement CRUD operations for main entities
3. Add authentication middleware for protected routes

### Step 5: Frontend
1. Create base template with navigation
2. Create index.html with main application interface
3. Implement JavaScript for API communication
4. Add CSS styling

### Step 6: Testing and Documentation
1. Create basic unit tests
2. Add README.md with setup instructions
3. Test all functionality end-to-end

## Dependencies
- Flask: Web framework
- SQLAlchemy: Database ORM
- Flask-Login: User session management
- Werkzeug: Password hashing utilities

## Security Considerations
- Use CSRF protection
- Implement proper password hashing
- Validate all user inputs
- Use secure session configuration
"""

        plan_file = Path(planning_child._state.working_dir) / "PLAN.md"
        with open(plan_file, "w") as f:
            f.write(plan_content)

        print(f"Created PLAN.md in {plan_file}")

        # Step 5: Create execution child (simulating the execute_plan tool)
        print("\n=== Step 5: Creating execution child ===")

        # Create an execution agent
        execution_agent = registry.create("execution", llm=llm)

        # Create execution child conversation from the planning child
        execution_child = planning_child.create_child_conversation(
            agent=execution_agent,
            visualize=False,
        )

        # Send plan execution message
        plan_file_path = Path(planning_child._state.working_dir) / "PLAN.md"
        if plan_file_path.exists():
            execution_message = (
                f"Please execute the plan found in PLAN.md. "
                f"The plan file is located at: {plan_file_path}\n\n"
                "Read the plan and implement each step systematically."
            )
        else:
            execution_message = (
                f"Please implement the following task:\n\n{complex_task}\n\n"
                "Break it down into steps and implement each one."
            )

        execution_child.send_message(execution_message)

        print("✅ Created execution child conversation")
        print(f"Execution Child ID: {execution_child._state.id}")
        print(f"Execution Working Directory: {execution_child._state.working_dir}")

        # Show child conversations hierarchy
        print("\n=== Child Conversations Hierarchy ===")

        # Main conversation children
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
        print("Workflow completed successfully:")
        print("1. ✅ ExecutionAgent created")
        print("2. ✅ Complex task received")
        print("3. ✅ PlanningAgent child spawned using spawn_planning_child tool")
        print("4. ✅ PLAN.md created by PlanningAgent")
        print("5. ✅ ExecutionAgent child spawned using execute_plan tool")
        print("6. ✅ Plan execution initiated")

        # Cleanup
        print("\n=== Cleanup ===")
        conversation.close()
        print("Closed all conversations")


if __name__ == "__main__":
    # Import agent configurations to trigger auto-registration

    main()
