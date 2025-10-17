#!/usr/bin/env python3
"""
TODO Agent for OpenHands Automated TODO Management

This script processes individual TODO(openhands) comments by:
1. Using OpenHands agent to implement the TODO (agent creates branch and PR)
2. Tracking the processing status and PR information for reporting

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
import sys
import warnings

from prompt import PROMPT

from openhands.sdk import LLM, Conversation, get_logger  # type: ignore
from openhands.tools.preset.default import get_default_agent  # type: ignore


# Suppress Pydantic serialization warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*PydanticSerializationUnexpectedValue.*")


logger = get_logger(__name__)


def process_todo(todo_data: dict) -> dict:
    """
    Process a single TODO item using OpenHands agent.

    Args:
        todo_data: Dictionary containing TODO information

    Returns:
        Dictionary containing processing results
    """
    file_path = todo_data["file"]
    line_num = todo_data["line"]
    description = todo_data["description"]

    logger.info(f"Processing TODO in {file_path}:{line_num}")

    # Initialize result structure
    result = {
        "todo": todo_data,
        "status": "failed",
        "error": None,
    }

    try:
        # Configure LLM
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            logger.error("LLM_API_KEY environment variable is not set.")
            result["error"] = "LLM_API_KEY environment variable is not set."
            return result

        model = os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929")
        base_url = os.getenv("LLM_BASE_URL")

        llm_config = {
            "model": model,
            "api_key": api_key,
            "service_id": "todo_agent",
            "drop_params": True,
        }

        if base_url:
            llm_config["base_url"] = base_url

        llm = LLM(**llm_config)

        # Create the prompt
        prompt = PROMPT.format(
            file_path=file_path,
            line_num=line_num,
            description=description,
        )

        # Get the current working directory as workspace
        cwd = os.getcwd()

        # Create agent with default tools
        agent = get_default_agent(
            llm=llm,
            cli_mode=True,
        )

        # Create conversation
        conversation = Conversation(
            agent=agent,
            workspace=cwd,
        )

        logger.info("Starting task execution...")
        logger.info(f"Prompt: {prompt[:200]}...")

        # Send the prompt and run the agent - trust it to handle everything
        conversation.send_message(prompt)
        conversation.run()

        # Mark as successful - trust the agent handled the task
        result["status"] = "success"
        logger.info("TODO processed successfully")

    except Exception as e:
        logger.error(f"Error processing TODO: {e}")
        result["error"] = str(e)
        result["status"] = "failed"

    return result


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
    required_fields = ["file", "line", "description"]
    for field in required_fields:
        if field not in todo_data:
            logger.error(f"Missing required field in TODO data: {field}")
            sys.exit(1)

    # Process the TODO and get results
    result = process_todo(todo_data)

    # Output result to a file for the workflow to collect
    result_file = (
        f"todo_result_{todo_data['file'].replace('/', '_')}_{todo_data['line']}.json"
    )
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)

    logger.info(f"Result written to {result_file}")
    logger.info(f"Processing result: {result['status']}")

    if result["error"]:
        logger.error(f"Error: {result['error']}")

    # Exit with appropriate code
    if result["status"] == "failed":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
