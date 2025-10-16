#!/usr/bin/env python3
"""
TODO Agent for OpenHands Automated TODO Management

This script processes individual TODO(openhands) comments by:
1. Using OpenHands agent to implement the TODO (agent creates branch and PR)
2. Updating the original TODO comment with the PR URL

Usage:
    python todo_agent.py <todo_json>

Arguments:
    todo_json: JSON string containing TODO information from todo_scanner.py

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
    result = run_git_command(['git', 'branch', '--show-current'])
    return result.stdout.strip()


def get_recent_branches() -> list[str]:
    """Get list of recent branches that might be feature branches."""
    result = run_git_command(['git', 'branch', '--sort=-committerdate'])
    branches = []
    for line in result.stdout.strip().split('\n'):
        branch = line.strip().lstrip('* ').strip()
        if branch and branch != 'main' and branch != 'master':
            branches.append(branch)
    return branches[:10]  # Get last 10 branches


def check_for_recent_pr(_todo_description: str) -> str | None:
    """
    Check if there's a recent PR that might be related to this TODO.
    This is a simple heuristic - in practice you might want to use GitHub API.
    """
    # For now, return None - this would need GitHub API integration
    return None


def update_todo_with_pr_url(
    file_path: str, 
    line_num: int, 
    pr_url: str,
    feature_branch: str | None = None
) -> None:
    """
    Update the TODO comment with PR URL on main branch and feature branch.
    
    Args:
        file_path: Path to the file containing the TODO
        line_num: Line number of the TODO comment
        pr_url: URL of the pull request
        feature_branch: Name of the feature branch (if known)
    """
    # Update on main branch
    current_branch = get_current_branch()
    
    # Switch to main branch
    if current_branch != 'main':
        run_git_command(['git', 'checkout', 'main'])
        run_git_command(['git', 'pull', 'origin', 'main'])
    
    # Read and update the file
    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()
    
    if line_num <= len(lines):
        original_line = lines[line_num - 1]
        if 'TODO(openhands)' in original_line and pr_url not in original_line:
            updated_line = original_line.replace(
                'TODO(openhands)',
                f'TODO(in progress: {pr_url})'
            )
            lines[line_num - 1] = updated_line
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            # Commit the change on main
            run_git_command(['git', 'add', file_path])
            run_git_command([
                'git', 'commit', '-m', 
                f'Update TODO with PR reference: {pr_url}'
            ])
            run_git_command(['git', 'push', 'origin', 'main'])
            
            # If we know the feature branch, update it there too
            if feature_branch:
                try:
                    # Switch to feature branch and merge the change
                    run_git_command(['git', 'checkout', feature_branch])
                    run_git_command(['git', 'merge', 'main', '--no-edit'])
                    run_git_command(['git', 'push', 'origin', feature_branch])
                except subprocess.CalledProcessError:
                    logger.warning(f"Could not update feature branch {feature_branch}")
                finally:
                    # Switch back to main
                    run_git_command(['git', 'checkout', 'main'])


def process_todo(todo_data: dict) -> None:
    """
    Process a single TODO item using OpenHands agent.
    
    Args:
        todo_data: Dictionary containing TODO information
    """
    file_path = todo_data['file']
    line_num = todo_data['line']
    description = todo_data['description']
    todo_text = todo_data['text']
    
    logger.info(f"Processing TODO in {file_path}:{line_num}")
    
    # Check required environment variables
    required_env_vars = ['LLM_API_KEY', 'GITHUB_TOKEN', 'GITHUB_REPOSITORY']
    for var in required_env_vars:
        if not os.getenv(var):
            logger.error(f"Required environment variable {var} is not set")
            sys.exit(1)
    
    # Set up LLM configuration
    llm_config = {
        'model': os.getenv('LLM_MODEL', 'openhands/claude-sonnet-4-5-20250929'),
        'api_key': SecretStr(os.getenv('LLM_API_KEY')),
    }
    
    if base_url := os.getenv('LLM_BASE_URL'):
        llm_config['base_url'] = base_url
    
    llm = LLM(**llm_config)
    
    # Create the prompt
    prompt = PROMPT.format(
        file_path=file_path,
        line_num=line_num,
        description=description,
        todo_text=todo_text
    )
    
    # Initialize conversation and agent
    conversation = Conversation()
    agent = get_default_agent(llm=llm)
    
    # Send the prompt to the agent
    logger.info("Sending TODO implementation request to agent")
    conversation.add_message(role='user', content=prompt)
    
    # Run the agent
    agent.run(conversation=conversation)
    
    # Check if agent created a PR
    # Look for PR URLs in the response
    pr_url = None
    feature_branch = None
    
    for message in conversation.messages:
        if message.role == 'assistant' and 'pull/' in message.content:
            # Extract PR URL from response
            import re
            pr_match = re.search(
                r'https://github\.com/[^/]+/[^/]+/pull/\d+', message.content
            )
            if pr_match:
                pr_url = pr_match.group(0)
                break
    
    if not pr_url:
        # Agent didn't create a PR, ask it to do so
        logger.info("Agent didn't create a PR, requesting one")
        follow_up = (
            "It looks like you haven't created a feature branch and pull request yet. "
            "Please create a feature branch for your changes and push them to create a "
            "pull request."
        )
        conversation.add_message(role='user', content=follow_up)
        agent.run(conversation=conversation)
        
        # Check again for PR URL
        for message in conversation.messages[-2:]:  # Check last 2 messages
            if message.role == 'assistant' and 'pull/' in message.content:
                import re
                pr_match = re.search(
                    r'https://github\.com/[^/]+/[^/]+/pull/\d+', message.content
                )
                if pr_match:
                    pr_url = pr_match.group(0)
                    break
    
    if pr_url:
        logger.info(f"Found PR URL: {pr_url}")
        # Try to determine the feature branch name
        recent_branches = get_recent_branches()
        if recent_branches:
            feature_branch = recent_branches[0]  # Most recent branch
        
        # Update the TODO comment
        update_todo_with_pr_url(file_path, line_num, pr_url, feature_branch)
        logger.info(f"Updated TODO comment with PR URL: {pr_url}")
    else:
        logger.warning("Could not find PR URL in agent response")
        logger.info("Agent response summary:")
        for message in conversation.messages[-3:]:
            if message.role == 'assistant':
                logger.info(f"Assistant: {message.content[:200]}...")


def main():
    """Main function to process a TODO item."""
    parser = argparse.ArgumentParser(
        description="Process a TODO(openhands) comment using OpenHands agent"
    )
    parser.add_argument(
        "todo_json",
        help="JSON string containing TODO information"
    )
    
    args = parser.parse_args()
    
    try:
        todo_data = json.loads(args.todo_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    
    # Validate required fields
    required_fields = ['file', 'line', 'description', 'text']
    for field in required_fields:
        if field not in todo_data:
            logger.error(f"Missing required field in TODO data: {field}")
            sys.exit(1)
    
    process_todo(todo_data)


if __name__ == "__main__":
    main()