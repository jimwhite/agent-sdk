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

import tempfile
from unittest.mock import patch

from litellm.types.utils import Choices, Message as LiteLLMMessage, ModelResponse, Usage
from pydantic import SecretStr

# Import agents to trigger auto-registration
import openhands.sdk.agent.agents  # noqa: F401
from openhands.sdk import LLM, Agent, LocalConversation, ToolSpec, register_tool
from openhands.tools.execute_bash import BashTool
from openhands.tools.str_replace_editor import FileEditorTool


COMPLEX_TASK = (
    "Create a simple calculator class with a Python module with basic arithmetic "
    "operations (add, subtract, multiply, divide)"
)


def create_mock_llm_responses():
    """Create mock LLM responses for the child conversation workflow."""

    # Define long JSON strings as variables to avoid line length issues
    plan_md_content = (
        "# Calculator Class Implementation Plan\\n\\n"
        "## Overview\\nCreate a simple calculator class with basic "
        "arithmetic operations and proper error handling.\\n\\n"
        "## Implementation Steps\\n\\n### 1. Create Calculator Class\\n"
        "- Define Calculator class with methods for basic operations\\n"
        "- add(a, b) - Addition\\n- subtract(a, b) - Subtraction\\n"
        "- multiply(a, b) - Multiplication\\n- divide(a, b) - Division "
        "with zero-division error handling\\n\\n### 2. Error Handling\\n"
        "- Handle division by zero\\n- Validate input types\\n"
        "- Provide meaningful error messages\\n\\n### 3. Documentation\\n"
        "- Add docstrings to class and methods\\n- Include usage "
        "examples\\n\\n### 4. Testing\\n- Create basic test cases\\n"
        "- Test normal operations\\n- Test error conditions\\n\\n"
        "### 5. Module Structure\\n- calculator.py - Main calculator "
        "class\\n- test_calculator.py - Test cases\\n- README.md - "
        "Usage documentation\\n\\n## Next Steps\\nUse execute_plan "
        "tool to delegate implementation to execution agent."
    )

    calculator_py_content = (
        'class Calculator:\\n    \\"\\"\\"\\n    '
        "A simple calculator class with basic arithmetic "
        'operations.\\n    \\"\\"\\"\\n\\n    def add(self, a, b):\\n        '
        '\\"\\"\\"Add two numbers.\\"\\"\\"\\n        return a + b\\n\\n    '
        'def subtract(self, a, b):\\n        \\"\\"\\"Subtract b from '
        'a.\\"\\"\\"\\n        return a - b\\n\\n    def multiply(self, '
        'a, b):\\n        \\"\\"\\"Multiply two numbers.\\"\\"\\"\\n        '
        "return a * b\\n\\n    def divide(self, a, b):\\n        "
        '\\"\\"\\"Divide a by b with zero-division error handling.'
        '\\"\\"\\"\\n        if b == 0:\\n            raise ValueError('
        '\\"Cannot divide by zero\\")\\n        return a / b\\n'
    )

    test_calculator_py_content = (
        "from calculator import Calculator\\n\\n"
        "def test_calculator():\\n    calc = Calculator()\\n    \\n    "
        "# Test addition\\n    assert calc.add(2, 3) == 5\\n    "
        'print(\\"Addition test passed\\")\\n    \\n    # Test '
        "subtraction\\n    assert calc.subtract(5, 3) == 2\\n    "
        'print(\\"Subtraction test passed\\")\\n    \\n    # Test '
        "multiplication\\n    assert calc.multiply(4, 3) == 12\\n    "
        'print(\\"Multiplication test passed\\")\\n    \\n    # Test '
        "division\\n    assert calc.divide(10, 2) == 5\\n    "
        'print(\\"Division test passed\\")\\n    \\n    # Test division '
        "by zero\\n    try:\\n        calc.divide(10, 0)\\n        "
        'assert False, \\"Should have raised ValueError\\"\\n    '
        "except ValueError as e:\\n        assert str(e) == "
        '\\"Cannot divide by zero\\"\\n        print(\\"Division by '
        'zero test passed\\")\\n    \\n    print(\\"All tests '
        'passed!\\")\\n\\nif __name__ == \\"__main__\\":\\n    '
        "test_calculator()\\n"
    )

    # Response 1: ExecutionAgent decides to use spawn_planning_child
    response1 = ModelResponse(
        id="mock-response-1",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "I'll help you create a calculator class. This is indeed a "
                        "complex task that requires planning. Let me use the "
                        "spawn_planning_child tool to create a detailed plan first."
                    ),
                    tool_calls=[
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "spawn_planning_child",
                                "arguments": (
                                    '{"task_description": "Create a simple calculator '
                                    "class with a Python module with basic arithmetic "
                                    "operations (add, subtract, multiply, divide). "
                                    "Include proper error handling, documentation, and "
                                    'basic tests."}'
                                ),
                            },
                        }
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
    )

    # Response 2: ExecutionAgent acknowledges the planning child creation
    response2 = ModelResponse(
        id="mock-response-2",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "Great! I've created a planning child conversation to analyze "
                        "this task. The planning agent will create a detailed plan for "
                        "implementing the calculator class."
                    ),
                ),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=150, completion_tokens=30, total_tokens=180),
    )

    # Response 3: PlanningAgent creates a detailed plan
    response3 = ModelResponse(
        id="mock-response-3",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "I'll analyze this task and create a comprehensive plan for "
                        "implementing a calculator class. Let me break this down into "
                        "clear steps."
                    ),
                    tool_calls=[
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "str_replace_editor",
                                "arguments": (
                                    f'{{"command": "create", "path": "PLAN.md", '
                                    f'"file_text": "{plan_md_content}"}}'
                                ),
                            },
                        }
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=Usage(prompt_tokens=200, completion_tokens=80, total_tokens=280),
    )

    # Response 4: PlanningAgent uses execute_plan tool
    response4 = ModelResponse(
        id="mock-response-4",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "Perfect! I've created a detailed plan for the calculator "
                        "implementation. Now I'll use the execute_plan tool to "
                        "delegate the actual implementation to an execution agent."
                    ),
                    tool_calls=[
                        {
                            "id": "call_3",
                            "type": "function",
                            "function": {
                                "name": "execute_plan",
                                "arguments": '{"plan_file": "PLAN.md"}',
                            },
                        }
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=Usage(prompt_tokens=280, completion_tokens=40, total_tokens=320),
    )

    # Response 5: ExecutionAgent (child) implements the calculator
    response5 = ModelResponse(
        id="mock-response-5",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "I'll implement the calculator class according to the plan. "
                        "Let me start by creating the main calculator module."
                    ),
                    tool_calls=[
                        {
                            "id": "call_4",
                            "type": "function",
                            "function": {
                                "name": "str_replace_editor",
                                "arguments": (
                                    f'{{"command": "create", "path": "calculator.py", '
                                    f'"file_text": "{calculator_py_content}"}}'
                                ),
                            },
                        }
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=Usage(prompt_tokens=320, completion_tokens=60, total_tokens=380),
    )

    # Response 6: ExecutionAgent creates test file
    response6 = ModelResponse(
        id="mock-response-6",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "Now I'll create a test file to verify the calculator "
                        "functionality."
                    ),
                    tool_calls=[
                        {
                            "id": "call_5",
                            "type": "function",
                            "function": {
                                "name": "str_replace_editor",
                                "arguments": (
                                    f'{{"command": "create", '
                                    f'"path": "test_calculator.py", '
                                    f'"file_text": "{test_calculator_py_content}"}}'
                                ),
                            },
                        }
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=Usage(prompt_tokens=380, completion_tokens=70, total_tokens=450),
    )

    # Response 7: ExecutionAgent runs the tests
    response7 = ModelResponse(
        id="mock-response-7",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "Let me run the tests to verify everything works correctly."
                    ),
                    tool_calls=[
                        {
                            "id": "call_6",
                            "type": "function",
                            "function": {
                                "name": "execute_bash",
                                "arguments": '{"command": "python test_calculator.py"}',
                            },
                        }
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        usage=Usage(prompt_tokens=450, completion_tokens=30, total_tokens=480),
    )

    # Response 8: ExecutionAgent completes the task
    response8 = ModelResponse(
        id="mock-response-8",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content=(
                        "Perfect! I've successfully implemented the calculator class "
                        "according to the plan. The implementation includes:\n\n"
                        "1. Calculator class with add, subtract, multiply, and divide "
                        "methods\n2. Proper error handling for division by zero\n"
                        "3. Comprehensive test suite that verifies all functionality\n"
                        "4. All tests are passing\n\nThe calculator module is now "
                        "ready for use!"
                    ),
                ),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=480, completion_tokens=50, total_tokens=530),
    )

    return [
        response1,
        response2,
        response3,
        response4,
        response5,
        response6,
        response7,
        response8,
    ]


"""Demonstrate the child conversation workflow."""


def main():
    """Main function with mocked LLM responses."""
    # Setup mock responses
    mock_responses = create_mock_llm_responses()

    with patch("openhands.sdk.llm.llm.litellm_completion") as mock_completion:
        mock_completion.side_effect = mock_responses

        # Configure LLM - using mock for testing
        llm = LLM(
            model="gpt-4o",
            api_key=SecretStr("test-key"),
            service_id="test-llm",
            num_retries=2,
            retry_min_wait=1,
            retry_max_wait=2,
        )
        print("Using mock LLM for testing")

        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Working directory: {temp_dir}")

            # Step 1: Create an ExecutionAgent with the specialized tools
            print("\n=== Step 1: Creating ExecutionAgent ===")

            # Register tools
            register_tool("BashTool", BashTool)
            register_tool("FileEditorTool", FileEditorTool)

            # Import and register the specialized tools
            from openhands.sdk.tool.tools.execute_plan import ExecutePlanTool
            from openhands.sdk.tool.tools.spawn_planning_child import (
                SpawnPlanningChildTool,
            )

            register_tool("SpawnPlanningChildTool", SpawnPlanningChildTool)
            register_tool("ExecutePlanTool", ExecutePlanTool)

            # Create execution agent with the specialized tools
            execution_agent = Agent(
                llm=llm,
                tools=[
                    ToolSpec(name="BashTool"),
                    ToolSpec(name="FileEditorTool"),
                    ToolSpec(name="SpawnPlanningChildTool"),
                ],
            )

            conversation = LocalConversation(
                agent=execution_agent,
                workspace=temp_dir,
                visualize=True,  # Enable visualization to see the workflow
            )

            print(f"Created conversation with ExecutionAgent: {conversation._state.id}")

            # Step 2: User asks a complex task requiring planning
            print("\n=== Step 2: User requests complex task ===")
            execution_agent_instruction = (
                f"I need you to {COMPLEX_TASK}. "
                "This is a complex task that requires planning. "
                "Please use the spawn_planning_child tool to create a detailed "
                "plan first, then execute that plan."
            )

            print(f"User request: {execution_agent_instruction}")

            # Step 3: Send the complex task to ExecutionAgent and run
            print("\n=== Step 3: ExecutionAgent processes complex task ===")
            print(
                "ExecutionAgent will use spawn_planning_child tool to create a "
                "planning child..."
            )

            conversation.send_message(execution_agent_instruction)
            conversation.run()

            print("\n=== Step 4: Checking Results ===")

            # Check if any files were created in the workspace
            import os

            workspace_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    workspace_files.append(file_path)

            print(f"Files created in workspace: {workspace_files}")

            # Look for the calculator files
            calculator_files = [f for f in workspace_files if "calculator" in f.lower()]
            if calculator_files:
                print(f"✅ Calculator files found: {calculator_files}")

                # Show content of the main calculator file
                for calc_file in calculator_files:
                    if calc_file.endswith(".py"):
                        print(f"\n--- Content of {calc_file} ---")
                        with open(calc_file) as f:
                            content = f.read()
                            print(
                                content[:1000] + ("..." if len(content) > 1000 else "")
                            )
                        break
            else:
                print("⚠️  No calculator files found")

            # Check if PLAN.md was created anywhere
            plan_files = [
                f for f in workspace_files if "PLAN.md" in f or "plan.md" in f
            ]
            if plan_files:
                print(f"✅ Plan files found: {plan_files}")

                # Show content of the plan
                for plan_file in plan_files:
                    print(f"\n--- Content of {plan_file} ---")
                    with open(plan_file) as f:
                        content = f.read()
                        print(content[:500] + ("..." if len(content) > 500 else ""))
                    break
            else:
                print("⚠️  No plan files found")

            print("\n=== Summary ===")
            print("Agent delegation workflow completed:")
            print("1. ✅ ExecutionAgent created with specialized tools")
            print("2. ✅ User sent complex task to ExecutionAgent")
            print("3. ✅ ExecutionAgent should have used spawn_planning_child tool")
            print(
                "4. ✅ Planning should have created PLAN.md and used execute_plan tool"
            )
            print("5. ✅ ExecutionAgent should have implemented the calculator")

            # Cleanup
            print("\n=== Cleanup ===")
            conversation.close()
            print("Closed conversation")


if __name__ == "__main__":
    main()
