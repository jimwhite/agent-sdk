"""
Automated TODO Management Example

This example demonstrates how to use the OpenHands SDK to automatically scan a codebase
for TODO(openhands) comments and create pull requests to implement them.

Features:
- Scans repository for TODO(openhands) patterns
- Extracts context around TODO comments
- Uses OpenHands to understand and implement solutions
- Creates branches and pull requests with implementations
- Handles duplicate detection to avoid multiple PRs for the same TODO
- Can be integrated with GitHub Actions for scheduled automation

Usage:
    python examples/20_automated_todo_management.py --repo-path /path/to/repo

Environment Variables:
    GITHUB_TOKEN: Required for creating pull requests
    LITELLM_API_KEY: Required for LLM operations
"""

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    get_logger,
)
from openhands.sdk.tool import ToolSpec, register_tool
from openhands.tools.execute_bash import BashTool
from openhands.tools.str_replace_editor import FileEditorTool


logger = get_logger(__name__)


@dataclass
class TodoItem:
    """Represents a TODO comment found in the codebase."""

    file_path: str
    line_number: int
    todo_text: str
    context_before: list[str]
    context_after: list[str]
    full_context: str
    unique_id: str

    def __post_init__(self):
        """Generate a unique ID for this TODO item."""
        if not self.unique_id:
            # Create a hash based on file path, line number, and TODO text
            import hashlib

            content = f"{self.file_path}:{self.line_number}:{self.todo_text}"
            self.unique_id = hashlib.md5(content.encode()).hexdigest()[:8]


class TodoScanner:
    """Scans a repository for TODO(openhands) comments."""

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.todo_pattern = re.compile(r"#\s*TODO\(openhands\):\s*(.+)", re.IGNORECASE)
        self.in_progress_pattern = re.compile(
            r"#\s*TODO\(openhands-in-progress\):\s*(.+)", re.IGNORECASE
        )

    def scan_repository(self) -> list[TodoItem]:
        """Scan the repository for TODO(openhands) comments."""
        todos = []

        # Find all Python files (can be extended to other file types)
        python_files = list(self.repo_path.rglob("*.py"))

        for file_path in python_files:
            # Skip virtual environments and build directories
            if any(
                part in file_path.parts
                for part in [".venv", "__pycache__", ".git", "node_modules"]
            ):
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    # Skip if this TODO is already in progress
                    if self.in_progress_pattern.search(line):
                        continue

                    match = self.todo_pattern.search(line)
                    if match:
                        todo_text = match.group(1).strip()

                        # Extract context (5 lines before and after)
                        context_start = max(0, line_num - 6)
                        context_end = min(len(lines), line_num + 5)

                        context_before = [
                            lines[i].rstrip()
                            for i in range(context_start, line_num - 1)
                        ]
                        context_after = [
                            lines[i].rstrip() for i in range(line_num, context_end)
                        ]

                        full_context = "\n".join(
                            context_before + [line.rstrip()] + context_after
                        )

                        todo = TodoItem(
                            file_path=str(file_path.relative_to(self.repo_path)),
                            line_number=line_num,
                            todo_text=todo_text,
                            context_before=context_before,
                            context_after=context_after,
                            full_context=full_context,
                            unique_id="",
                        )
                        todos.append(todo)

            except Exception as e:
                logger.warning(f"Error reading file {file_path}: {e}")
                continue

        return todos


class GitHubPRManager:
    """Manages GitHub operations for creating pull requests."""

    def __init__(self, repo_owner: str, repo_name: str, github_token: str):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def create_branch(self, branch_name: str, base_branch: str = "main") -> bool:
        """Create a new branch from the base branch."""
        try:
            # Get the SHA of the base branch
            response = requests.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/git/refs/heads/{base_branch}",
                headers=self.headers,
            )
            response.raise_for_status()
            base_sha = response.json()["object"]["sha"]

            # Create the new branch
            data = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
            response = requests.post(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/git/refs",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Error creating branch {branch_name}: {e}")
            return False

    def create_pull_request(
        self, branch_name: str, title: str, body: str, base_branch: str = "main"
    ) -> dict[str, Any] | None:
        """Create a pull request."""
        try:
            data = {
                "title": title,
                "body": body,
                "head": branch_name,
                "base": base_branch,
                "draft": True,  # Create as draft initially
            }
            response = requests.post(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls",
                headers=self.headers,
                json=data,
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error creating pull request: {e}")
            return None

    def check_existing_prs(self, todo_id: str) -> bool:
        """Check if a PR already exists for this TODO."""
        try:
            response = requests.get(
                f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/pulls",
                headers=self.headers,
                params={"state": "all"},
            )
            response.raise_for_status()

            for pr in response.json():
                if f"todo-{todo_id}" in pr.get("head", {}).get("ref", ""):
                    return True
            return False

        except Exception as e:
            logger.error(f"Error checking existing PRs: {e}")
            return False


class TodoImplementer:
    """Uses OpenHands to implement TODO items."""

    def __init__(self, llm: LLM, repo_path: str):
        self.llm = llm
        self.repo_path = repo_path

        # Register tools
        register_tool("BashTool", BashTool)
        register_tool("FileEditorTool", FileEditorTool)

        self.tool_specs = [
            ToolSpec(name="BashTool", params={"working_dir": repo_path}),
            ToolSpec(name="FileEditorTool", params={"workspace_root": repo_path}),
        ]

        self.agent = Agent(llm=llm, tools=self.tool_specs)

    def implement_todo(self, todo: TodoItem) -> tuple[bool, str]:
        """
        Implement a TODO item using OpenHands.

        Returns:
            tuple: (success, implementation_summary)
        """
        try:
            # Create a conversation for this TODO
            conversation = Conversation(agent=self.agent)

            # Prepare the prompt
            prompt = self._create_implementation_prompt(todo)

            # Send the message and run the conversation
            conversation.send_message(prompt)
            conversation.run()

            # Get the final response
            final_response = self._get_final_response(conversation)

            return True, final_response

        except Exception as e:
            logger.error(f"Error implementing TODO {todo.unique_id}: {e}")
            return False, str(e)

    def _create_implementation_prompt(self, todo: TodoItem) -> str:
        """Create a detailed prompt for implementing the TODO."""
        return f"""
I need you to implement a TODO comment found in the codebase. Here are the details:

**File:** {todo.file_path}
**Line:** {todo.line_number}
**TODO Text:** {todo.todo_text}

**Context around the TODO:**
```
{todo.full_context}
```

**Instructions:**
1. Analyze the TODO comment and understand what needs to be implemented
2. Look at the surrounding code context to understand the current implementation
3. Implement the requested functionality or fix
4. If it's a test-related TODO, write appropriate tests
5. Make sure your implementation follows the existing code style and patterns
6. Update the TODO comment to mark it as completed by changing it to:
   `# TODO(openhands-completed): {todo.todo_text}`

**Important:**
- Only modify files that are necessary for the implementation
- Follow existing code patterns and conventions
- Write clean, well-documented code
- If you need to understand more about the codebase, use the available tools to explore

Please implement this TODO and provide a summary of what you did.
"""

    def _get_final_response(self, conversation: Conversation) -> str:
        """Extract the final response from the conversation."""
        from openhands.sdk.event import MessageEvent
        from openhands.sdk.llm import TextContent

        events = list(conversation.state.events)

        # Look for the last message event from the agent
        for event in reversed(events):
            if isinstance(event, MessageEvent) and event.source == "agent":
                # Extract text content from the message
                content_parts = []
                for content_item in event.llm_message.content:
                    if isinstance(content_item, TextContent):
                        content_parts.append(content_item.text)
                if content_parts:
                    return " ".join(content_parts)

        return "Implementation completed successfully."


class AutomatedTodoManager:
    """Main class that orchestrates the TODO management process."""

    def __init__(
        self,
        repo_path: str,
        repo_owner: str,
        repo_name: str,
        github_token: str,
        llm: LLM,
        config_path: str | None = None,
    ):
        self.repo_path = repo_path
        self.scanner = TodoScanner(repo_path)
        self.pr_manager = GitHubPRManager(repo_owner, repo_name, github_token)
        self.implementer = TodoImplementer(llm, repo_path)
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: str | None) -> dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            "max_todos_per_run": 3,
            "branch_prefix": "openhands/todo-",
            "pr_title_template": "Implement TODO: {todo_text}",
            "pr_body_template": """
This PR implements a TODO comment found in the codebase.

**TODO Details:**
- File: {file_path}
- Line: {line_number}
- Description: {todo_text}

**Implementation Summary:**
{implementation_summary}

**Context:**
```
{context}
```

This PR was automatically generated by the OpenHands TODO management system.
""",
            "exclude_patterns": [".venv", "__pycache__", ".git", "node_modules"],
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Error loading config from {config_path}: {e}")

        return default_config

    def run(self, dry_run: bool = False) -> dict[str, Any]:
        """
        Run the automated TODO management process.

        Args:
            dry_run: If True, only scan and report without making changes

        Returns:
            dict: Summary of the run results
        """
        logger.info("Starting automated TODO management...")

        # Scan for TODOs
        todos = self.scanner.scan_repository()
        logger.info(f"Found {len(todos)} TODO(openhands) comments")

        if not todos:
            return {
                "status": "success",
                "message": "No TODOs found",
                "todos_processed": 0,
            }

        if dry_run:
            return {
                "status": "success",
                "message": f"Dry run: Found {len(todos)} TODOs",
                "todos": [
                    {
                        "file": todo.file_path,
                        "line": todo.line_number,
                        "text": todo.todo_text,
                        "id": todo.unique_id,
                    }
                    for todo in todos
                ],
            }

        # Process TODOs (limit based on config)
        max_todos = self.config.get("max_todos_per_run", 3)
        todos_to_process = todos[:max_todos]

        results = []
        for todo in todos_to_process:
            result = self._process_todo(todo)
            results.append(result)

        return {
            "status": "success",
            "todos_processed": len(results),
            "results": results,
        }

    def _process_todo(self, todo: TodoItem) -> dict[str, Any]:
        """Process a single TODO item."""
        logger.info(
            f"Processing TODO {todo.unique_id} in {todo.file_path}:{todo.line_number}"
        )

        # Check if PR already exists
        if self.pr_manager.check_existing_prs(todo.unique_id):
            logger.info(f"PR already exists for TODO {todo.unique_id}, skipping")
            return {
                "todo_id": todo.unique_id,
                "status": "skipped",
                "reason": "PR already exists",
            }

        # Mark TODO as in progress
        self._mark_todo_in_progress(todo)

        try:
            # Implement the TODO
            success, implementation_summary = self.implementer.implement_todo(todo)

            if not success:
                self._unmark_todo_in_progress(todo)
                return {
                    "todo_id": todo.unique_id,
                    "status": "failed",
                    "reason": f"Implementation failed: {implementation_summary}",
                }

            # Create branch and commit changes
            branch_name = f"{self.config['branch_prefix']}{todo.unique_id}"

            if not self._create_branch_and_commit(
                branch_name, todo, implementation_summary
            ):
                self._unmark_todo_in_progress(todo)
                return {
                    "todo_id": todo.unique_id,
                    "status": "failed",
                    "reason": "Failed to create branch or commit changes",
                }

            # Create pull request
            pr_title = self.config["pr_title_template"].format(todo_text=todo.todo_text)
            pr_body = self.config["pr_body_template"].format(
                file_path=todo.file_path,
                line_number=todo.line_number,
                todo_text=todo.todo_text,
                implementation_summary=implementation_summary,
                context=todo.full_context,
            )

            pr_result = self.pr_manager.create_pull_request(
                branch_name, pr_title, pr_body
            )

            if pr_result:
                return {
                    "todo_id": todo.unique_id,
                    "status": "success",
                    "pr_url": pr_result["html_url"],
                    "pr_number": pr_result["number"],
                }
            else:
                self._unmark_todo_in_progress(todo)
                return {
                    "todo_id": todo.unique_id,
                    "status": "failed",
                    "reason": "Failed to create pull request",
                }

        except Exception as e:
            self._unmark_todo_in_progress(todo)
            logger.error(f"Error processing TODO {todo.unique_id}: {e}")
            return {"todo_id": todo.unique_id, "status": "failed", "reason": str(e)}

    def _mark_todo_in_progress(self, todo: TodoItem) -> None:
        """Mark a TODO as in progress to prevent duplicate processing."""
        file_path = Path(self.repo_path) / todo.file_path

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Replace the TODO line
            line_index = todo.line_number - 1
            original_line = lines[line_index]
            updated_line = original_line.replace(
                "TODO(openhands):", "TODO(openhands-in-progress):"
            )
            lines[line_index] = updated_line

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        except Exception as e:
            logger.error(f"Error marking TODO as in progress: {e}")

    def _unmark_todo_in_progress(self, todo: TodoItem) -> None:
        """Unmark a TODO as in progress (revert to original state)."""
        file_path = Path(self.repo_path) / todo.file_path

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Revert the TODO line
            line_index = todo.line_number - 1
            original_line = lines[line_index]
            updated_line = original_line.replace(
                "TODO(openhands-in-progress):", "TODO(openhands):"
            )
            lines[line_index] = updated_line

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

        except Exception as e:
            logger.error(f"Error unmarking TODO as in progress: {e}")

    def _create_branch_and_commit(
        self, branch_name: str, todo: TodoItem, implementation_summary: str
    ) -> bool:
        """Create a branch and commit the changes."""
        try:
            # Create branch via GitHub API
            if not self.pr_manager.create_branch(branch_name):
                return False

            # Switch to the new branch locally
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            # Add and commit changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            commit_message = (
                f"Implement TODO: {todo.todo_text}\n\n"
                f"File: {todo.file_path}:{todo.line_number}\n"
                f"Implementation: {implementation_summary}\n\n"
                f"Co-authored-by: openhands <openhands@all-hands.dev>"
            )

            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            # Push the branch
            subprocess.run(
                ["git", "push", "origin", branch_name],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )

            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git operation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating branch and commit: {e}")
            return False


def main():
    """Main entry point for the automated TODO management system."""
    parser = argparse.ArgumentParser(
        description="Automated TODO Management with OpenHands"
    )
    parser.add_argument(
        "--repo-path", required=True, help="Path to the repository to scan"
    )
    parser.add_argument("--repo-owner", required=True, help="GitHub repository owner")
    parser.add_argument("--repo-name", required=True, help="GitHub repository name")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only scan and report, don't make changes",
    )

    args = parser.parse_args()

    # Check required environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is required")
        return 1

    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        logger.error("LITELLM_API_KEY environment variable is required")
        return 1

    # Load config to get LLM settings
    config = {}
    if args.config:
        try:
            with open(args.config, "r") as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file: {e}")

    # Configure LLM from config or use defaults
    llm_config = config.get("llm_config", {})
    model = llm_config.get("model", "litellm_proxy/anthropic/claude-sonnet-4-20250514")
    base_url = llm_config.get("base_url", "https://llm-proxy.eval.all-hands.dev")

    llm = LLM(
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
        temperature=llm_config.get("temperature", 0.0),
        max_output_tokens=llm_config.get("max_tokens", 64000),
    )

    # Create and run the TODO manager
    manager = AutomatedTodoManager(
        repo_path=args.repo_path,
        repo_owner=args.repo_owner,
        repo_name=args.repo_name,
        github_token=github_token,
        llm=llm,
        config_path=args.config,
    )

    try:
        results = manager.run(dry_run=args.dry_run)

        print("=" * 80)
        print("Automated TODO Management Results")
        print("=" * 80)
        print(f"Status: {results['status']}")
        print(f"TODOs processed: {results.get('todos_processed', 0)}")

        if "results" in results:
            for result in results["results"]:
                print(f"\nTODO {result['todo_id']}: {result['status']}")
                if result["status"] == "success":
                    print(f"  PR: {result['pr_url']}")
                elif result["status"] == "failed":
                    print(f"  Reason: {result['reason']}")

        if "todos" in results:
            print("\nFound TODOs:")
            for todo in results["todos"]:
                print(f"  {todo['file']}:{todo['line']} - {todo['text']}")

        return 0

    except Exception as e:
        logger.error(f"Error running TODO management: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
