#!/usr/bin/env python3
"""
TODO Agent for OpenHands Automated TODO Management

This script processes individual TODO(openhands) comments by:
1. Using OpenHands agent to implement the TODO (agent creates branch and PR)
2. Updating the original TODO comment with the PR URL

Usage:
    python agent.py <todo_json>

Arguments:
    todo_json: JSON string containing TODO information from scanner.py

Environment Variables:
    LLM_API_KEY: API key for the LLM (required)
    LLM_MODEL: Language model to use (default: openhands/claude-sonnet-4-5-20250929)
    LLM_BASE_URL: Optional base URL for LLM API
    GITHUB_TOKEN: GitHub token for creating PRs (required)
    GITHUB_REPOSITORY: Repository in format owner/repo (required)

For setup instructions and usage examples, see README.md in this directory.
"""

import argparse
import json
import os
import subprocess
import sys

from prompt import PROMPT
from pydantic import SecretStr

from openhands.sdk import LLM, Conversation, get_logger
from openhands.tools.preset.default import get_default_agent


logger = get_logger(__name__)


def run_git_command(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the result."""
    logger.info(f"Running git command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if check and result.returncode != 0:
        logger.error(f"Git command failed: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)

    return result


def get_current_branch() -> str:
    """Get the current git branch name."""
    result = run_git_command(["git", "branch", "--show-current"])
    return result.stdout.strip()


def find_pr_for_branch(branch_name: str) -> str | None:
    """
    Find the PR URL for a given branch using GitHub API.

    Args:
        branch_name: Name of the feature branch

    Returns:
        PR URL if found, None otherwise
    """

    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        return None

    # Get repository info from git remote
    try:
        remote_result = run_git_command(["git", "remote", "get-url", "origin"])
        remote_url = remote_result.stdout.strip()

        # Extract owner/repo from remote URL
        import re

        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
        if not match:
            logger.error(f"Could not parse GitHub repo from remote URL: {remote_url}")
            return None

        owner, repo = match.groups()
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get git remote URL: {e}")
        return None

    # Search for PRs with this head branch
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    params = f"?head={owner}:{branch_name}&state=open"

    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                "-H",
                f"Authorization: token {github_token}",
                "-H",
                "Accept: application/vnd.github.v3+json",
                f"{api_url}{params}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        prs = json.loads(result.stdout)

        if prs and len(prs) > 0:
            return prs[0]["html_url"]  # Return the first (should be only) PR
        else:
            logger.warning(f"No open PR found for branch {branch_name}")
            return None

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logger.error(f"Failed to search for PR: {e}")
        return None


def update_todo_with_pr_url(
    file_path: str, line_num: int, pr_url: str, feature_branch: str
) -> None:
    """
    Update the TODO comment with PR URL on main branch and feature branch.

    Args:
        file_path: Path to the file containing the TODO
        line_num: Line number of the TODO comment
        pr_url: URL of the pull request
        feature_branch: Name of the feature branch
    """
    # Switch to main branch to update the TODO
    run_git_command(["git", "checkout", "main"])
    run_git_command(["git", "pull", "origin", "main"])

    # Read and update the file
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()

    if line_num <= len(lines):
        original_line = lines[line_num - 1]
        if "TODO(openhands)" in original_line and pr_url not in original_line:
            updated_line = original_line.replace(
                "TODO(openhands)", f"TODO(in progress: {pr_url})"
            )
            lines[line_num - 1] = updated_line

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            # Commit the change on main branch
            run_git_command(["git", "add", file_path])
            run_git_command(
                ["git", "commit", "-m", f"Update TODO with PR reference: {pr_url}"]
            )
            run_git_command(["git", "push", "origin", "main"])

            # Update the feature branch too
            try:
                # Switch to feature branch and merge the change
                run_git_command(["git", "checkout", feature_branch])
                run_git_command(["git", "merge", "main", "--no-edit"])
                run_git_command(["git", "push", "origin", feature_branch])
            except subprocess.CalledProcessError:
                logger.warning(f"Could not update feature branch {feature_branch}")
            finally:
                # Switch back to main
                run_git_command(["git", "checkout", "main"])


def process_todo(todo_data: dict) -> None:
    """
    Process a single TODO item using OpenHands agent.

    Args:
        todo_data: Dictionary containing TODO information
    """
    file_path = todo_data["file"]
    line_num = todo_data["line"]
    description = todo_data["description"]
    todo_text = todo_data["text"]

    logger.info(f"Processing TODO in {file_path}:{line_num}")

    # Check required environment variables
    required_env_vars = ["LLM_API_KEY", "GITHUB_TOKEN", "GITHUB_REPOSITORY"]
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Required environment variable {var} is not set")
            sys.exit(1)

    # Set up LLM configuration
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        logger.error("LLM_API_KEY is required")
        sys.exit(1)

    llm_config = {
        "model": os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929"),
        "api_key": SecretStr(api_key),
    }

    if base_url := os.getenv("LLM_BASE_URL"):
        llm_config["base_url"] = base_url

    llm = LLM(**llm_config)

    # Create the prompt
    prompt = PROMPT.format(
        file_path=file_path,
        line_num=line_num,
        description=description,
        todo_text=todo_text,
    )

    # Initialize agent and conversation
    agent = get_default_agent(llm=llm)
    conversation = Conversation(agent=agent)

    # Send the prompt to the agent
    logger.info("Sending TODO implementation request to agent")
    conversation.send_message(prompt)

    # Store the initial branch (should be main)
    initial_branch = get_current_branch()

    # Run the agent
    conversation.run()

    # After agent runs, check if we're on a different branch (feature branch)
    current_branch = get_current_branch()

    if current_branch != initial_branch:
        # Agent created a feature branch, find the PR for it
        logger.info(f"Agent switched from {initial_branch} to {current_branch}")
        pr_url = find_pr_for_branch(current_branch)

        if pr_url:
            logger.info(f"Found PR URL: {pr_url}")
            # Update the TODO comment
            update_todo_with_pr_url(file_path, line_num, pr_url, current_branch)
            logger.info(f"Updated TODO comment with PR URL: {pr_url}")
        else:
            logger.warning(f"Could not find PR for branch {current_branch}")
    else:
        # Agent didn't create a feature branch, ask it to do so
        logger.info("Agent didn't create a feature branch, requesting one")
        follow_up = (
            "It looks like you haven't created a feature branch and pull request yet. "
            "Please create a feature branch for your changes and push them to create a "
            "pull request."
        )
        conversation.send_message(follow_up)
        conversation.run()

        # Check again for branch change
        current_branch = get_current_branch()
        if current_branch != initial_branch:
            pr_url = find_pr_for_branch(current_branch)
            if pr_url:
                logger.info(f"Found PR URL: {pr_url}")
                update_todo_with_pr_url(file_path, line_num, pr_url, current_branch)
                logger.info(f"Updated TODO comment with PR URL: {pr_url}")
            else:
                logger.warning(f"Could not find PR for branch {current_branch}")
        else:
            logger.warning("Agent still didn't create a feature branch")


def main():
    """Main function to process a TODO item."""
    parser = argparse.ArgumentParser(
        description="Process a TODO(openhands) comment using OpenHands agent"
    )
    parser.add_argument("todo_json", help="JSON string containing TODO information")

    args = parser.parse_args()

    try:
        todo_data = json.loads(args.todo_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)

    # Validate required fields
    required_fields = ["file", "line", "description", "text"]
    for field in required_fields:
        if field not in todo_data:
            logger.error(f"Missing required field in TODO data: {field}")
            sys.exit(1)

    process_todo(todo_data)


if __name__ == "__main__":
    main()
