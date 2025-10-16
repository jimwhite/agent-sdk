#!/usr/bin/env python3
"""
TODO Agent for OpenHands Automated TODO Management

This script processes individual TODO(openhands) comments by:
1. Creating a feature branch
2. Using OpenHands agent to implement the TODO
3. Creating a pull request
4. Updating the original TODO comment with the PR URL

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
import uuid
from pathlib import Path

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
        raise subprocess.CalledProcessError(
            result.returncode, cmd, result.stdout, result.stderr
        )
    
    return result


def create_feature_branch(todo_info: dict) -> str:
    """Create a feature branch for the TODO implementation."""
    # Generate a unique branch name based on the TODO
    file_name = Path(todo_info['file']).stem
    line_num = todo_info['line']
    unique_id = str(uuid.uuid4())[:8]
    
    branch_name = f"openhands/todo-{file_name}-line{line_num}-{unique_id}"
    
    # Ensure we're on main/master branch
    try:
        run_git_command(['git', 'checkout', 'main'])
    except subprocess.CalledProcessError:
        try:
            run_git_command(['git', 'checkout', 'master'])
        except subprocess.CalledProcessError:
            logger.warning(
                "Could not checkout main or master branch, "
                "continuing from current branch"
            )
    
    # Pull latest changes
    try:
        run_git_command(['git', 'pull', 'origin', 'HEAD'])
    except subprocess.CalledProcessError:
        logger.warning("Could not pull latest changes, continuing with current state")
    
    # Create and checkout feature branch
    run_git_command(['git', 'checkout', '-b', branch_name])
    
    return branch_name


def generate_todo_prompt(todo_info: dict) -> str:
    """Generate a prompt for the OpenHands agent to implement the TODO."""
    file_path = todo_info['file']
    line_num = todo_info['line']
    description = todo_info['description']
    content = todo_info['content']
    context = todo_info['context']
    
    # Build context information
    context_info = ""
    if context['before']:
        context_info += "Lines before the TODO:\n"
        start_line = line_num - len(context['before'])
        for i, line in enumerate(context['before'], start=start_line):
            context_info += f"{i}: {line}\n"
    
    context_info += f"{line_num}: {content}\n"
    
    if context['after']:
        context_info += "Lines after the TODO:\n"
        for i, line in enumerate(context['after'], start=line_num+1):
            context_info += f"{i}: {line}\n"
    
    prompt = f"""I need you to implement a TODO comment found in the codebase.

**TODO Details:**
- File: {file_path}
- Line: {line_num}
- Content: {content}
- Description: {description or "No specific description provided"}

**Context around the TODO:**
```
{context_info}
```

**Instructions:**
1. Analyze the TODO comment and understand what needs to be implemented
2. Look at the surrounding code context to understand the codebase structure
3. Implement the required functionality following the existing code patterns and style
4. Remove or update the TODO comment once the implementation is complete
5. Ensure your implementation is well-tested and follows best practices
6. If the TODO requires significant changes, break them down into logical steps

**Important Notes:**
- Follow the existing code style and patterns in the repository
- Add appropriate tests if the codebase has a testing structure
- Make sure your implementation doesn't break existing functionality
- If you need to make assumptions about the requirements, document them clearly
- Focus on creating a minimal, working implementation that addresses the TODO

Please implement this TODO and provide a clear summary of what you've done."""

    return prompt


def create_pull_request(branch_name: str, todo_info: dict) -> str:
    """Create a pull request for the TODO implementation."""
    github_token = os.getenv('GITHUB_TOKEN')
    github_repo = os.getenv('GITHUB_REPOSITORY')
    
    if not github_token or not github_repo:
        logger.error(
            "GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required"
        )
        raise ValueError("Missing GitHub configuration")
    
    # Generate PR title and body
    file_name = Path(todo_info['file']).name
    description = todo_info['description'] or "implementation"
    
    title = f"Implement TODO in {file_name}:{todo_info['line']} - {description}"
    
    body = f"""## Automated TODO Implementation

This PR was automatically created by the OpenHands TODO management system.

**TODO Details:**
- **File:** `{todo_info['file']}`
- **Line:** {todo_info['line']}
- **Original Comment:** `{todo_info['content']}`
- **Description:** {todo_info['description'] or "No specific description provided"}

**Implementation:**
This PR implements the functionality described in the TODO comment. The implementation 
follows the existing code patterns and includes appropriate tests where applicable.

**Context:**
The TODO was automatically detected and implemented using the OpenHands agent system. 
Please review the changes and merge if they meet the project's standards.

---
*This PR was created automatically by OpenHands TODO Management*
"""
    
    # Use GitHub CLI to create the PR
    cmd = [
        'gh', 'pr', 'create',
        '--title', title,
        '--body', body,
        '--head', branch_name,
        '--base', 'main'  # Try main first
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        pr_url = result.stdout.strip()
        logger.info(f"Created pull request: {pr_url}")
        return pr_url
    except subprocess.CalledProcessError as e:
        # Try with master as base if main fails
        if 'main' in ' '.join(cmd):
            cmd[-1] = 'master'
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                pr_url = result.stdout.strip()
                logger.info(f"Created pull request: {pr_url}")
                return pr_url
            except subprocess.CalledProcessError:
                pass
        
        logger.error(f"Failed to create pull request: {e.stderr}")
        raise


def update_todo_with_pr_url(todo_info: dict, pr_url: str):
    """Update the original TODO comment with the PR URL."""
    file_path = Path(todo_info['file'])
    line_num = todo_info['line']
    
    # Read the file
    with open(file_path, encoding='utf-8') as f:
        lines = f.readlines()
    
    # Update the TODO line
    if line_num <= len(lines):
        original_line = lines[line_num - 1]
        # Replace the TODO comment with a reference to the PR
        updated_line = original_line.replace(
            'TODO(openhands)',
            f'TODO(openhands: {pr_url})'
        )
        lines[line_num - 1] = updated_line
        
        # Write the file back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        logger.info(f"Updated TODO comment in {file_path}:{line_num} with PR URL")
        
        # Commit the change to main branch
        try:
            # Switch back to main branch
            run_git_command(['git', 'checkout', 'main'])
            
            # Pull latest changes
            run_git_command(['git', 'pull', 'origin', 'main'])
            
            # Make the change again (in case of conflicts)
            with open(file_path, encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_num <= len(lines):
                original_line = lines[line_num - 1]
                if 'TODO(openhands)' in original_line and pr_url not in original_line:
                    updated_line = original_line.replace(
                        'TODO(openhands)',
                        f'TODO(openhands: {pr_url})'
                    )
                    lines[line_num - 1] = updated_line
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    # Stage and commit the change
                    run_git_command(['git', 'add', str(file_path)])
                    commit_msg = f'Update TODO comment with PR URL: {pr_url}'
                    run_git_command(['git', 'commit', '-m', commit_msg])
                    run_git_command(['git', 'push', 'origin', 'main'])
                    
                    logger.info("Successfully updated main branch with PR URL")
        
        except subprocess.CalledProcessError as e:
            logger.warning(f"Could not update main branch with PR URL: {e}")
            # This is not critical, the PR still exists


def main():
    """Process a single TODO item."""
    parser = argparse.ArgumentParser(
        description="Process a TODO(openhands) comment with OpenHands agent"
    )
    parser.add_argument(
        "todo_json",
        help="JSON string containing TODO information"
    )
    
    args = parser.parse_args()
    
    # Parse TODO information
    try:
        todo_info = json.loads(args.todo_json)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        sys.exit(1)
    
    # Validate required environment variables
    api_key = os.getenv("LLM_API_KEY")
    github_token = os.getenv("GITHUB_TOKEN")
    github_repo = os.getenv("GITHUB_REPOSITORY")
    
    if not api_key:
        logger.error("LLM_API_KEY environment variable is not set.")
        sys.exit(1)
    
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable is not set.")
        sys.exit(1)
    
    if not github_repo:
        logger.error("GITHUB_REPOSITORY environment variable is not set.")
        sys.exit(1)
    
    logger.info(f"Processing TODO: {todo_info['file']}:{todo_info['line']}")
    
    try:
        # Create feature branch
        branch_name = create_feature_branch(todo_info)
        logger.info(f"Created feature branch: {branch_name}")
        
        # Configure LLM
        model = os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929")
        base_url = os.getenv("LLM_BASE_URL")
        
        llm_config = {
            "model": model,
            "api_key": SecretStr(api_key),
            "service_id": "todo_agent",
            "drop_params": True,
        }
        
        if base_url:
            llm_config["base_url"] = base_url
        
        llm = LLM(**llm_config)
        
        # Create agent with default tools
        agent = get_default_agent(
            llm=llm,
            cli_mode=True,
        )
        
        # Create conversation
        conversation = Conversation(
            agent=agent,
            workspace=os.getcwd(),
        )
        
        # Generate and send prompt
        prompt = generate_todo_prompt(todo_info)
        logger.info("Starting TODO implementation...")
        logger.info(f"Prompt: {prompt[:200]}...")
        
        conversation.send_message(prompt)
        conversation.run()
        
        # Commit changes
        run_git_command(['git', 'add', '.'])
        description = todo_info['description'] or 'Automated TODO implementation'
        commit_message = (
            f"Implement TODO in {todo_info['file']}:{todo_info['line']}\n\n"
            f"{description}"
        )
        run_git_command(['git', 'commit', '-m', commit_message])
        
        # Push the branch
        run_git_command(['git', 'push', 'origin', branch_name])
        
        # Create pull request
        pr_url = create_pull_request(branch_name, todo_info)
        
        # Update the original TODO with PR URL
        update_todo_with_pr_url(todo_info, pr_url)
        
        logger.info(f"Successfully processed TODO. PR created: {pr_url}")
        
    except Exception as e:
        logger.error(f"Failed to process TODO: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()