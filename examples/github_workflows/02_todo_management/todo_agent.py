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


def get_pr_info(pr_url: str) -> dict | None:
    """
    Extract PR information from GitHub API using the PR URL.
    
    Args:
        pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
    
    Returns:
        Dictionary with PR info including head and base branch names, or None if failed
    """
    import re
    import subprocess
    
    # Extract owner, repo, and PR number from URL
    match = re.match(r'https://github\.com/([^/]+)/([^/]+)/pull/(\d+)', pr_url)
    if not match:
        logger.error(f"Invalid PR URL format: {pr_url}")
        return None
    
    owner, repo, pr_number = match.groups()
    
    # Get GitHub token from environment
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        return None
    
    # Call GitHub API to get PR information
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    
    try:
        result = subprocess.run([
            'curl', '-s', '-H', f'Authorization: token {github_token}',
            '-H', 'Accept: application/vnd.github.v3+json',
            api_url
        ], capture_output=True, text=True, check=True)
        
        import json
        pr_data = json.loads(result.stdout)
        
        return {
            'head_branch': pr_data['head']['ref'],
            'base_branch': pr_data['base']['ref'],
            'head_repo': pr_data['head']['repo']['full_name'],
            'base_repo': pr_data['base']['repo']['full_name']
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to get PR info from GitHub API: {e}")
        return None


def update_todo_with_pr_url(file_path: str, line_num: int, pr_url: str) -> None:
    """
    Update the TODO comment with PR URL on main branch and feature branch.
    
    Args:
        file_path: Path to the file containing the TODO
        line_num: Line number of the TODO comment
        pr_url: URL of the pull request
    """
    # Get PR information from GitHub API
    pr_info = get_pr_info(pr_url)
    if not pr_info:
        logger.error("Could not get PR information from GitHub API")
        return
    
    feature_branch = pr_info['head_branch']
    base_branch = pr_info['base_branch']
    
    logger.info(f"PR info: {feature_branch} -> {base_branch}")
    
    # Update on base branch (usually main)
    current_branch = get_current_branch()
    
    # Switch to base branch
    if current_branch != base_branch:
        run_git_command(['git', 'checkout', base_branch])
        run_git_command(['git', 'pull', 'origin', base_branch])
    
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
            
            # Commit the change on base branch
            run_git_command(['git', 'add', file_path])
            run_git_command([
                'git', 'commit', '-m', 
                f'Update TODO with PR reference: {pr_url}'
            ])
            run_git_command(['git', 'push', 'origin', base_branch])
            
            # Update the feature branch too
            try:
                # Switch to feature branch and merge the change
                run_git_command(['git', 'checkout', feature_branch])
                run_git_command(['git', 'merge', base_branch, '--no-edit'])
                run_git_command(['git', 'push', 'origin', feature_branch])
            except subprocess.CalledProcessError:
                logger.warning(f"Could not update feature branch {feature_branch}")
            finally:
                # Switch back to base branch
                run_git_command(['git', 'checkout', base_branch])


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
        # Update the TODO comment using GitHub API to get branch info
        update_todo_with_pr_url(file_path, line_num, pr_url)
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