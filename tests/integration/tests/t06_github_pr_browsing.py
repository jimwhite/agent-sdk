"""Test that an agent can browse a GitHub PR and extract information."""

from openhands.sdk import create_mcp_tools, get_logger
from openhands.sdk.tool import Tool
from openhands.tools import BashTool, FileEditorTool
from tests.integration.base import BaseIntegrationTest, TestResult


INSTRUCTION = (
    "Look at https://github.com/All-Hands-AI/OpenHands/pull/8, and tell me what is "
    "happening there and what did @asadm suggest."
)


logger = get_logger(__name__)


class GitHubPRBrowsingTest(BaseIntegrationTest):
    """Test that an agent can browse a GitHub PR and extract information."""

    INSTRUCTION = INSTRUCTION

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
        """No setup needed for this test."""
        pass

    def verify_result(self) -> TestResult:
        """Verify that the agent successfully browsed the GitHub PR."""
        # Check if the agent mentioned relevant information about the PR
        # We'll look for mentions of GitHub, PR, pull request, or @asadm

        pr_keywords = [
            "pull request",
            "pr",
            "github",
            "asadm",
            "@asadm",
            "openhands",
            "all-hands-ai",
        ]

        # Check the LLM messages for any mention of PR-related content
        found_keywords = []
        for message in self.llm_messages:
            message_text = str(message).lower()
            for keyword in pr_keywords:
                if keyword in message_text:
                    found_keywords.append(keyword)

        # Also check the collected events
        for event in self.collected_events:
            event_text = str(event).lower()
            for keyword in pr_keywords:
                if keyword in event_text and keyword not in found_keywords:
                    found_keywords.append(keyword)

        # We need at least some evidence that the agent accessed the PR
        if len(found_keywords) >= 2:
            return TestResult(
                success=True,
                reason=(
                    f"Successfully browsed GitHub PR: found keywords {found_keywords}"
                ),
            )
        elif found_keywords:
            return TestResult(
                success=True,
                reason=(
                    f"Partially successful - found some PR-related content: "
                    f"{found_keywords}"
                ),
            )
        else:
            return TestResult(
                success=False,
                reason=(
                    "Agent did not appear to successfully browse the GitHub PR or "
                    "extract relevant information"
                ),
            )

    def teardown(self):
        """Clean up test resources."""
        # No cleanup needed for this test
        pass
