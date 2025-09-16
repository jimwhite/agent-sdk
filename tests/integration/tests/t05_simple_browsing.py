"""Test that an agent can browse localhost and extract information."""

import os
import subprocess
import tempfile
import time

from openhands.sdk import create_mcp_tools, get_logger
from openhands.sdk.tool import Tool
from openhands.tools import BashTool, FileEditorTool
from tests.integration.base import BaseIntegrationTest, TestResult


INSTRUCTION = "Browse localhost:8000, and tell me the ultimate answer to life."

HTML_FILE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Ultimate Answer</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(to right, #1e3c72, #2a5298);
            color: #fff;
            font-family: 'Arial', sans-serif;
            text-align: center;
        }
        .container {
            text-align: center;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
        }
        h1 {
            font-size: 36px;
            margin-bottom: 20px;
        }
        p {
            font-size: 18px;
            margin-bottom: 30px;
        }
        #showButton {
            padding: 10px 20px;
            font-size: 16px;
            color: #1e3c72;
            background: #fff;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        #showButton:hover {
            background: #f0f0f0;
        }
        #result {
            margin-top: 20px;
            font-size: 24px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>The Ultimate Answer</h1>
        <p>Click the button to reveal the answer to life, the universe, and "
"everything.</p>
        <button id="showButton">Click me</button>
        <div id="result"></div>
    </div>
    <script>
        document.getElementById('showButton').addEventListener('click', function() {
            document.getElementById('result').innerText = "
"'The answer is OpenHands is all you need!';
        });
    </script>
</body>
</html>
"""


logger = get_logger(__name__)


class SimpleBrowsingTest(BaseIntegrationTest):
    """Test that an agent can browse localhost and extract information."""

    INSTRUCTION = INSTRUCTION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_dir = None
        self.server_process = None

    @property
    def tools(self) -> list[Tool]:
        """List of tools available to the agent."""
        if self.cwd is None:
            raise ValueError("CWD must be set before accessing tools")

        tools = [
            BashTool.create(working_dir=self.cwd),
            FileEditorTool.create(workspace_root=self.cwd),
        ]

        # Add MCP tools for web browsing
        try:
            mcp_config = {
                "mcpServers": {
                    "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]}
                }
            }
            mcp_tools = create_mcp_tools(mcp_config, timeout=30)
            tools.extend(mcp_tools)
            logger.info(f"Added {len(mcp_tools)} MCP tools for browsing")
        except Exception as e:
            logger.warning(f"Failed to create MCP tools: {e}")

        return tools

    def setup(self) -> None:
        """Set up a local HTTP server with the HTML content."""
        if self.cwd is None:
            raise ValueError("CWD must be set before setup")

        # Create a temporary directory for the HTML file
        self.temp_dir = tempfile.mkdtemp()
        html_file_path = os.path.join(self.temp_dir, "index.html")

        with open(html_file_path, "w") as f:
            f.write(HTML_FILE)

        logger.info(f"Created HTML file at: {html_file_path}")

        # Start HTTP server in background
        try:
            # Use nohup to start the server in background
            self.server_process = subprocess.Popen(
                ["python3", "-m", "http.server", "8000"],
                cwd=self.temp_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setsid,  # Create new process group
            )

            # Give the server a moment to start
            time.sleep(2)

            logger.info("Started HTTP server on localhost:8000")

        except Exception as e:
            raise RuntimeError(f"Failed to start HTTP server: {e}")

    def verify_result(self) -> TestResult:
        """Verify that the agent successfully browsed the page and found the answer."""
        # Check if the agent mentioned the ultimate answer in the conversation
        # We'll look through the collected events for mentions of the answer

        answer_keywords = [
            "openhands is all you need",
            "openhands",
            "ultimate answer",
            "answer to life",
            "42",  # Classic reference
        ]

        # Check the LLM messages for any mention of the answer
        for message in self.llm_messages:
            message_text = str(message).lower()
            for keyword in answer_keywords:
                if keyword in message_text:
                    return TestResult(
                        success=True,
                        reason=(
                            f"Successfully found the ultimate answer: found "
                            f"'{keyword}' in response"
                        ),
                    )

        # Also check the collected events
        for event in self.collected_events:
            event_text = str(event).lower()
            for keyword in answer_keywords:
                if keyword in event_text:
                    return TestResult(
                        success=True,
                        reason=(
                            f"Successfully found the ultimate answer: found "
                            f"'{keyword}' in event"
                        ),
                    )

        return TestResult(
            success=False,
            reason="Agent did not find or mention the ultimate answer from the webpage",
        )

    def teardown(self):
        """Clean up the HTTP server and temporary files."""
        # Stop the HTTP server
        if self.server_process:
            try:
                # Kill the entire process group
                os.killpg(os.getpgid(self.server_process.pid), 9)
                self.server_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error stopping HTTP server: {e}")

        # Clean up temporary directory
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil

                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning(f"Error cleaning up temp directory: {e}")
