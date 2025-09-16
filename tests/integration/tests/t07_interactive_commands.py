"""Test that an agent can execute interactive Python script with input."""

import hashlib
import os

from openhands.sdk import get_logger
from openhands.sdk.tool import Tool
from openhands.tools import BashTool, FileEditorTool
from tests.integration.base import BaseIntegrationTest, TestResult


INSTRUCTION = (
    'Execute the python script /workspace/python_script.py with input "John" and "25" '
    "and tell me the secret number."
)

# Calculate the expected secret number
SECRET_NUMBER = int(hashlib.sha256(str(25).encode()).hexdigest()[:8], 16) % 1000


logger = get_logger(__name__)


class InteractiveCommandsTest(BaseIntegrationTest):
    """Test that an agent can execute interactive Python script with input."""

    INSTRUCTION = INSTRUCTION

    @property
    def tools(self) -> list[Tool]:
        """List of tools available to the agent."""
        if self.cwd is None:
            raise ValueError("CWD must be set before accessing tools")
        return [
            BashTool.create(working_dir=self.cwd),
            FileEditorTool.create(workspace_root=self.cwd),
        ]

    def setup(self) -> None:
        """Create the workspace directory and Python script."""
        if self.cwd is None:
            raise ValueError("CWD must be set before setup")

        # Create the workspace directory
        workspace_dir = os.path.join(self.cwd, "workspace")
        os.makedirs(workspace_dir, exist_ok=True)

        # Create the interactive Python script
        script_path = os.path.join(workspace_dir, "python_script.py")
        script_content = (
            'name = input("Enter your name: ")\n'
            'age = input("Enter your age: ")\n'
            "import hashlib\n"
            "secret = int(hashlib.sha256(str(age).encode()).hexdigest()[:8], 16) % "
            "1000\n"
            'print(f"Hello {name}, you are {age} years old. '
            'Tell you a secret number: {secret}")\n'
        )

        with open(script_path, "w") as f:
            f.write(script_content)

        logger.info(f"Created interactive Python script at: {script_path}")
        logger.info(f"Expected secret number for age 25: {SECRET_NUMBER}")

    def verify_result(self) -> TestResult:
        """Verify that the agent successfully executed the script and found the secret number."""  # noqa: E501
        # Check if the agent mentioned the secret number in the conversation
        secret_str = str(SECRET_NUMBER)

        # Check the LLM messages for the secret number
        for message in self.llm_messages:
            message_text = str(message)
            if secret_str in message_text:
                return TestResult(
                    success=True,
                    reason=f"Successfully found the secret number: {SECRET_NUMBER}",
                )

        # Also check the collected events
        for event in self.collected_events:
            event_text = str(event)
            if secret_str in event_text:
                return TestResult(
                    success=True,
                    reason=f"Successfully found the secret number: {SECRET_NUMBER}",
                )

        # Check for partial success - if the agent at least tried to run the script
        execution_keywords = [
            "python_script.py",
            "Enter your name",
            "Enter your age",
            "John",
            "25",
            "secret number",
            "Hello John",
        ]

        found_keywords = []
        for message in self.llm_messages:
            message_text = str(message).lower()
            for keyword in execution_keywords:
                if keyword.lower() in message_text and keyword not in found_keywords:
                    found_keywords.append(keyword)

        for event in self.collected_events:
            event_text = str(event).lower()
            for keyword in execution_keywords:
                if keyword.lower() in event_text and keyword not in found_keywords:
                    found_keywords.append(keyword)

        if len(found_keywords) >= 3:
            return TestResult(
                success=False,
                reason=(
                    f"Agent executed the script but did not find the correct "
                    f"secret number {SECRET_NUMBER}. Found keywords: {found_keywords}"
                ),
            )
        else:
            return TestResult(
                success=False,
                reason=(
                    "Agent did not successfully execute the interactive Python script"
                ),
            )

    def teardown(self):
        """Clean up test resources."""
        # Note: In this implementation, cwd is managed externally
        # so we don't need to clean it up here
        pass
