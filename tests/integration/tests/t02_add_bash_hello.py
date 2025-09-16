"""Test that an agent can write a shell script that prints 'hello'."""

import os
import subprocess

from openhands.sdk import get_logger
from openhands.sdk.tool import Tool
from openhands.tools import BashTool, FileEditorTool
from tests.integration.base import BaseIntegrationTest, TestResult


INSTRUCTION = "Write a shell script '/workspace/hello.sh' that prints 'hello'."


logger = get_logger(__name__)


class BashHelloTest(BaseIntegrationTest):
    """Test that an agent can write a shell script that prints 'hello'."""

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
        """Create the workspace directory."""
        if self.cwd is None:
            raise ValueError("CWD must be set before setup")

        # Create the workspace directory
        workspace_dir = os.path.join(self.cwd, "workspace")
        os.makedirs(workspace_dir, exist_ok=True)
        logger.info(f"Created workspace directory at: {workspace_dir}")

    def verify_result(self) -> TestResult:
        """Verify that the agent successfully created the shell script."""
        if self.cwd is None:
            return TestResult(success=False, reason="CWD not set")

        script_path = os.path.join(self.cwd, "workspace", "hello.sh")

        if not os.path.exists(script_path):
            return TestResult(
                success=False,
                reason="Shell script file not found at /workspace/hello.sh",
            )

        # Check if the script is executable
        if not os.access(script_path, os.X_OK):
            return TestResult(success=False, reason="Shell script is not executable")

        # Read the script content
        with open(script_path, "r") as f:
            script_content = f.read()

        # Check if the script contains the expected output
        if "hello" not in script_content.lower():
            return TestResult(
                success=False,
                reason=f"Script does not contain 'hello': {script_content}",
            )

        # Try to execute the script and check output
        try:
            result = subprocess.run(
                ["bash", script_path],
                capture_output=True,
                text=True,
                cwd=self.cwd,
                timeout=10,
            )

            if result.returncode != 0:
                return TestResult(
                    success=False,
                    reason=(
                        f"Script execution failed with return code "
                        f"{result.returncode}: {result.stderr}"
                    ),
                )

            if "hello" not in result.stdout.lower():
                return TestResult(
                    success=False,
                    reason=f"Script output does not contain 'hello': {result.stdout}",
                )

            return TestResult(
                success=True, reason="Successfully created and executed shell script"
            )

        except subprocess.TimeoutExpired:
            return TestResult(success=False, reason="Script execution timed out")
        except Exception as e:
            return TestResult(success=False, reason=f"Error executing script: {str(e)}")

    def teardown(self):
        """Clean up test resources."""
        # Note: In this implementation, cwd is managed externally
        # so we don't need to clean it up here
        pass
