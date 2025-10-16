#!/usr/bin/env python3
"""
Full workflow test for TODO management system.

This script tests the complete workflow:
1. Scan for TODOs
2. Run agent to implement each TODO
3. Validate the implementation
4. Simulate PR creation

This provides end-to-end testing without requiring GitHub Actions.
"""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
    ]
)
logger = logging.getLogger(__name__)


def run_scanner():
    """Run the scanner to find TODOs."""
    logger.info("🔍 Running TODO scanner...")
    
    result = subprocess.run(
        [sys.executable, "scanner.py", "../../.."],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent,
    )
    
    if result.returncode != 0:
        logger.error(f"Scanner failed: {result.stderr}")
        return []
    
    try:
        todos = json.loads(result.stdout)
        logger.info(f"Found {len(todos)} TODO(s)")
        return todos
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse scanner output: {e}")
        return []


def test_agent_implementation(todo):
    """Test the agent implementation for a specific TODO."""
    logger.info(f"🤖 Testing agent implementation for TODO: {todo['description']}")
    
    # Create a temporary directory for the test
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Copy the file to the temp directory
        original_file = Path(todo['file']).resolve()
        if not original_file.exists():
            logger.error(f"Original file not found: {original_file}")
            return False
            
        temp_file = temp_path / "test_file.py"
        temp_file.write_text(original_file.read_text())
        
        # Prepare the agent command
        agent_cmd = [
            sys.executable, "agent.py",
            "--file", str(temp_file),
            "--line", str(todo['line']),
            "--description", todo['description'],
            "--repo-root", str(Path("../../..").resolve())
        ]
        
        logger.info(f"Running agent command: {' '.join(agent_cmd)}")
        
        # Set environment variables for the agent
        env = os.environ.copy()
        env.update({
            'LLM_API_KEY': os.getenv('LLM_API_KEY', ''),
            'LLM_BASE_URL': os.getenv('LLM_BASE_URL', ''),
            'LLM_MODEL': os.getenv('LLM_MODEL', 'openhands/claude-sonnet-4-5-20250929'),
        })
        
        # Check if we have the required environment variables
        if not env.get('LLM_API_KEY'):
            logger.warning("⚠️  LLM_API_KEY not set - agent test will be skipped")
            logger.info("   To test the agent, set LLM_API_KEY environment variable")
            return True  # Skip test but don't fail
        
        # Run the agent
        result = subprocess.run(
            agent_cmd,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent,
            env=env,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Agent failed: {result.stderr}")
            logger.error(f"Agent stdout: {result.stdout}")
            return False
        
        # Check if the file was modified
        modified_content = temp_file.read_text()
        original_content = original_file.read_text()
        
        if modified_content == original_content:
            logger.warning("⚠️  Agent didn't modify the file")
            return False
        
        # Basic validation - check if the TODO was addressed
        if "TODO(openhands)" in modified_content:
            # Check if it was updated with progress indicator
            if "TODO(in progress:" in modified_content or "TODO(implemented:" in modified_content:
                logger.info("✅ TODO was updated with progress indicator")
            else:
                logger.warning("⚠️  TODO still exists without progress indicator")
        else:
            logger.info("✅ TODO was removed (likely implemented)")
        
        # Log the changes made
        logger.info("📝 Changes made by agent:")
        original_lines = original_content.splitlines()
        modified_lines = modified_content.splitlines()
        
        # Simple diff to show what changed
        for i, (orig, mod) in enumerate(zip(original_lines, modified_lines)):
            if orig != mod:
                logger.info(f"   Line {i+1}: '{orig}' -> '{mod}'")
        
        # Check for new lines added
        if len(modified_lines) > len(original_lines):
            for i in range(len(original_lines), len(modified_lines)):
                logger.info(f"   Line {i+1} (new): '{modified_lines[i]}'")
        
        logger.info("✅ Agent implementation test completed successfully")
        return True


def simulate_pr_creation(todo, implementation_success):
    """Simulate PR creation for a TODO."""
    logger.info(f"📋 Simulating PR creation for TODO: {todo['description']}")
    
    if not implementation_success:
        logger.warning("⚠️  Skipping PR creation - implementation failed")
        return False
    
    # Simulate PR creation logic
    branch_name = f"todo-{todo['line']}-{hash(todo['description']) % 10000}"
    pr_title = f"Implement TODO: {todo['description'][:50]}..."
    
    logger.info(f"   Branch name: {branch_name}")
    logger.info(f"   PR title: {pr_title}")
    logger.info("   PR body would contain:")
    logger.info(f"     - File: {todo['file']}")
    logger.info(f"     - Line: {todo['line']}")
    logger.info(f"     - Description: {todo['description']}")
    logger.info("     - Implementation details from agent")
    
    # Simulate updating the original TODO with PR URL
    fake_pr_url = f"https://github.com/All-Hands-AI/agent-sdk/pull/{1000 + todo['line']}"
    logger.info(f"   Would update TODO to: # TODO(in progress: {fake_pr_url}): {todo['description']}")
    
    logger.info("✅ PR creation simulation completed")
    return True


def main():
    """Run the full workflow test."""
    logger.info("🧪 Testing Full TODO Management Workflow")
    logger.info("=" * 50)
    
    # Step 1: Scan for TODOs
    todos = run_scanner()
    if not todos:
        logger.warning("⚠️  No TODOs found - nothing to test")
        return True
    
    logger.info(f"📋 Found {len(todos)} TODO(s) to process:")
    for i, todo in enumerate(todos, 1):
        logger.info(f"   {i}. {todo['file']}:{todo['line']} - {todo['description']}")
    
    # Step 2: Process each TODO
    success_count = 0
    for i, todo in enumerate(todos, 1):
        logger.info(f"\n🔄 Processing TODO {i}/{len(todos)}")
        logger.info("-" * 30)
        
        # Test agent implementation
        implementation_success = test_agent_implementation(todo)
        
        # Simulate PR creation
        pr_success = simulate_pr_creation(todo, implementation_success)
        
        if implementation_success and pr_success:
            success_count += 1
            logger.info(f"✅ TODO {i} processed successfully")
        else:
            logger.error(f"❌ TODO {i} processing failed")
    
    # Summary
    logger.info(f"\n📊 Workflow Test Summary")
    logger.info("=" * 30)
    logger.info(f"   TODOs found: {len(todos)}")
    logger.info(f"   Successfully processed: {success_count}")
    logger.info(f"   Failed: {len(todos) - success_count}")
    
    if success_count == len(todos):
        logger.info("🎉 All TODOs processed successfully!")
        return True
    else:
        logger.error(f"❌ {len(todos) - success_count} TODOs failed processing")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)