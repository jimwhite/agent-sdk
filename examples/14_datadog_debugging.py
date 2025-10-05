#!/usr/bin/env python3
"""
Datadog Debugging Example

This example demonstrates how to use the OpenHands agent to debug errors
logged in Datadog.
The agent will:
1. Query Datadog logs to understand the error using curl commands
2. Clone relevant GitHub repositories using git commands
3. Analyze the codebase to identify potential causes
4. Attempt to reproduce the error
5. Optionally create a draft PR with a fix

Usage:
    # Local execution
    python 14_datadog_debugging.py --query "status:error service:deploy" \\
        --repos "All-Hands-AI/OpenHands,All-Hands-AI/deploy"

    # Remote execution with Docker sandbox
    python 14_datadog_debugging.py --query "status:error service:deploy" \\
        --repos "All-Hands-AI/OpenHands,All-Hands-AI/deploy" \\
        --remote --docker

Environment Variables Required:
    - DATADOG_API_KEY: Your Datadog API key
    - DATADOG_APP_KEY: Your Datadog application key
    - GITHUB_TOKEN: Your GitHub personal access token
    - LLM_API_KEY: API key for the LLM service
"""

import argparse
import os
import sys
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    LLMConvertibleEvent,
    Message,
    RemoteConversation,
    TextContent,
    get_logger,
)
from openhands.sdk.tool import Tool, register_tool
from openhands.sdk.workspace import DockerWorkspace, Workspace
from openhands.tools.execute_bash import BashTool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool


logger = get_logger(__name__)


def validate_environment():
    """Validate that all required environment variables are set."""
    required_vars = [
        "DATADOG_API_KEY",
        "DATADOG_APP_KEY",
        "GITHUB_TOKEN",
        "LLM_API_KEY",
    ]

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("\nPlease set the following environment variables:")
        for var in missing_vars:
            print(f"  export {var}=your_key_here")
        return False

    return True


def create_debugging_prompt(query: str, repos: list[str]) -> str:
    """Create the debugging prompt for the agent."""
    repos_list = "\n".join(f"- {repo}" for repo in repos)

    return (
        "Your task is to debug an error on Datadog to find out why it is "
        "happening. To read DataDog logs, you should use the Datadog API "
        "via curl commands with your DATADOG_API_KEY and DATADOG_APP_KEY "
        "environment variables.\n\n"
        "To query Datadog logs, use the Logs API:\n"
        "```bash\n"
        "curl -X POST 'https://api.datadoghq.com/api/v2/logs/events/search' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -H 'DD-API-KEY: $DATADOG_API_KEY' \\\n"
        "  -H 'DD-APPLICATION-KEY: $DATADOG_APP_KEY' \\\n"
        "  -d '{\n"
        '    "filter": {\n'
        '      "query": "YOUR_QUERY_HERE",\n'
        '      "from": "now-1d",\n'
        '      "to": "now"\n'
        "    },\n"
        '    "sort": "timestamp",\n'
        '    "page": {\n'
        '      "limit": 10\n'
        "    }\n"
        "  }'\n"
        "```\n\n"
        "The Datadog query syntax supports:\n"
        "- status:error - Find error logs\n"
        "- service:my-service - Filter by service\n"
        '- "exact phrase" - Search for exact text\n'
        "- -(status:info OR status:debug) - Exclude certain statuses\n"
        "- Use time ranges to focus on recent issues\n\n"
        "The error class that I would like you to debug is characterized "
        f"by this datadog query:\n{query}\n\n"
        "To clone the GitHub repositories, use git with authentication:\n"
        "```bash\n"
        "git clone https://$GITHUB_TOKEN@github.com/OWNER/REPO.git\n"
        "```\n\n"
        "The github repos that you should clone (using GITHUB_TOKEN) are "
        f"the following:\n{repos_list}\n\n"
        "The steps to debug are:\n"
        "1. Get an understanding of the error by reading the error messages "
        "from 3-5 instances found through the Datadog API query.\n"
        "2. Check when the error class started occurring/becoming frequent "
        "to understand what code changes or release may have caused the "
        "changes. Keep in mind that all code that was changed during the "
        "release cycle before the error occurred will be the most "
        "suspicious.\n"
        "3. Carefully read the codebases included in repos that you "
        "downloaded and think carefully about the issue. Think of 5 "
        "possible reasons and test and see if you can write sample code "
        "that reproduces the error in any of them.\n"
        "4. If you are not able to reproduce the error message that you "
        "saw in the logs, finish right away and summarize your findings.\n"
        "5. If you were able to reproduce the error message that you saw "
        "in the logs, you can modify the code and open a draft PR that "
        "could fix the problem.\n\n"
        "Use the task_tracker tool to organize your work and keep track "
        "of your progress through these steps."
    )


def main():
    """Main function to run the Datadog debugging example."""
    parser = argparse.ArgumentParser(
        description="Debug errors from Datadog logs using OpenHands agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Datadog query to search for error logs "
        "(e.g., 'status:error service:deploy')",
    )
    parser.add_argument(
        "--repos",
        required=True,
        help="Comma-separated list of GitHub repositories to analyze "
        "(e.g., 'All-Hands-AI/OpenHands,All-Hands-AI/deploy')",
    )
    parser.add_argument(
        "--working-dir",
        default="./datadog_debug_workspace",
        help="Working directory for cloning repos and analysis "
        "(default: ./datadog_debug_workspace)",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Use remote execution via API server or Docker",
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Use Docker sandbox for remote execution (requires --remote)",
    )
    parser.add_argument(
        "--api-server",
        type=str,
        help="API server URL for remote execution (e.g., http://localhost:8000)",
    )
    parser.add_argument(
        "--docker-image",
        default="nikolaik/python-nodejs:python3.12-nodejs22",
        help="Docker image to use for sandboxed execution "
        "(default: nikolaik/python-nodejs:python3.12-nodejs22)",
    )
    parser.add_argument(
        "--docker-port",
        type=int,
        default=8010,
        help="Host port for Docker workspace API (default: 8010)",
    )

    args = parser.parse_args()

    # Validate environment
    if not validate_environment():
        sys.exit(1)

    # Validate remote execution options
    if args.docker and not args.remote:
        print("❌ --docker requires --remote flag")
        sys.exit(1)

    if args.api_server and args.docker:
        print("❌ Cannot use both --api-server and --docker")
        sys.exit(1)

    # Parse repositories
    repos = [repo.strip() for repo in args.repos.split(",")]

    # Create working directory (only for local execution)
    if not args.remote:
        working_dir = Path(args.working_dir).resolve()
        working_dir.mkdir(exist_ok=True)
    else:
        working_dir = Path(args.working_dir)

    print("🔍 Starting Datadog debugging session")
    print(f"📊 Query: {args.query}")
    print(f"📁 Repositories: {', '.join(repos)}")
    print(f"💼 Working directory: {working_dir}")
    if args.remote:
        if args.docker:
            print(f"🐳 Using Docker sandbox: {args.docker_image}")
        elif args.api_server:
            print(f"🌐 Using remote API server: {args.api_server}")
    print()

    # Configure LLM
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        print("❌ LLM_API_KEY environment variable is required")
        sys.exit(1)

    # Get LLM configuration from environment
    model = os.getenv("LLM_MODEL", "openhands/claude-sonnet-4-5-20250929")
    base_url = os.getenv("LLM_BASE_URL")

    llm = LLM(
        model=model,
        base_url=base_url,
        api_key=SecretStr(api_key),
    )

    # Determine if we need a workspace context manager
    workspace_context = None
    if args.remote and args.docker:
        logger.info("Setting up Docker workspace...")
        workspace_context = DockerWorkspace(
            base_image=args.docker_image,
            host_port=args.docker_port,
            forward_env=[
                "DATADOG_API_KEY",
                "DATADOG_APP_KEY",
                "GITHUB_TOKEN",
                "LLM_API_KEY",
            ],
        )

    # Run with or without workspace context manager
    if workspace_context:
        with workspace_context as workspace:
            _run_debugging_session(
                llm, workspace, working_dir, args.query, repos, args.remote
            )
    else:
        workspace = None
        if args.remote and args.api_server:
            logger.info(f"Connecting to remote API server: {args.api_server}")
            workspace = Workspace(host=args.api_server)
            # Test workspace
            result = workspace.execute_command("pwd")
            logger.info(f"Remote workspace directory: {result.stdout}")
        elif args.remote:
            print("❌ --remote requires either --docker or --api-server")
            sys.exit(1)

        _run_debugging_session(
            llm, workspace, working_dir, args.query, repos, args.remote
        )


def _run_debugging_session(
    llm: LLM,
    workspace,
    working_dir: Path,
    query: str,
    repos: list[str],
    is_remote: bool,
):
    """Run the debugging session with the given configuration."""
    # Register and set up tools
    register_tool("BashTool", BashTool)
    register_tool("FileEditorTool", FileEditorTool)
    register_tool("TaskTrackerTool", TaskTrackerTool)

    tools = [
        Tool(name="BashTool"),
        Tool(name="FileEditorTool"),
        Tool(name="TaskTrackerTool"),
    ]

    # Create agent
    agent = Agent(llm=llm, tools=tools)

    # Collect LLM messages for debugging
    llm_messages = []

    def conversation_callback(event: Event):
        if isinstance(event, LLMConvertibleEvent):
            llm_messages.append(event.to_llm_message())

    # Start conversation
    if workspace:
        conversation = Conversation(
            agent=agent, workspace=workspace, callbacks=[conversation_callback]
        )
        assert isinstance(conversation, RemoteConversation)
        logger.info(f"Remote conversation ID: {conversation.state.id}")
    else:
        conversation = Conversation(agent=agent, callbacks=[conversation_callback])

    # Send the debugging task
    debugging_prompt = create_debugging_prompt(query, repos)

    conversation.send_message(
        message=Message(
            role="user",
            content=[TextContent(text=debugging_prompt)],
        )
    )

    print("🤖 Starting debugging analysis...")
    try:
        conversation.run()

        print("\n" + "=" * 80)
        print("🎯 Debugging session completed!")
        print(f"📁 Results saved in: {working_dir}")
        print(f"💬 Total LLM messages: {len(llm_messages)}")

        # Show summary of what was accomplished
        print("\n📋 Session Summary:")
        print("- Queried Datadog logs for error analysis")
        print("- Cloned and analyzed relevant repositories")
        print("- Investigated potential root causes")
        print("- Attempted error reproduction")

        if not is_remote and working_dir.exists():
            cloned_repos = [
                d for d in working_dir.iterdir() if d.is_dir() and (d / ".git").exists()
            ]
            if cloned_repos:
                print(
                    f"- Cloned repositories: {', '.join(d.name for d in cloned_repos)}"
                )
    finally:
        # Clean up conversation
        logger.info("Closing conversation...")
        conversation.close()


if __name__ == "__main__":
    main()
