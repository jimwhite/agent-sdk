#!/usr/bin/env python3
"""
Debug script for TODO Management Workflow

This script:
1. Triggers the TODO management workflow on GitHub
2. Waits for it to complete (blocking)
3. Outputs errors if any occur OR URLs of PRs created by the workflow
4. Shows detailed logs throughout the process

Usage:
    python debug_workflow.py [--max-todos N] [--file-pattern PATTERN]

Arguments:
    --max-todos: Maximum number of TODOs to process (default: 3)
    --file-pattern: File pattern to scan (optional)

Environment Variables:
    GITHUB_TOKEN: GitHub token for API access (required)

Example:
    python debug_workflow.py --max-todos 2
"""

import argparse
import json
import os
import sys
import time


def make_github_request(
    method: str, endpoint: str, data: dict | None = None
) -> tuple[int, dict]:
    """Make a GitHub API request using curl."""
    import subprocess

    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "curl",
        "-s",
        "-w",
        "\\n%{http_code}",
        "-X",
        method,
        "-H",
        f"Authorization: token {github_token}",
        "-H",
        "Accept: application/vnd.github.v3+json",
        "-H",
        "User-Agent: debug-workflow-script",
    ]

    if data:
        cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])

    cmd.append(f"https://api.github.com{endpoint}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
        status_code = int(lines[-1])
        response_text = "\n".join(lines[:-1])

        if response_text:
            response_data = json.loads(response_text)
        else:
            response_data = {}

        return status_code, response_data
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        print(f"Error making GitHub API request: {e}", file=sys.stderr)
        return 500, {"error": str(e)}


def get_repo_info() -> tuple[str, str]:
    """Get repository owner and name from git remote."""
    import re
    import subprocess

    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        remote_url = result.stdout.strip()

        # Extract owner/repo from remote URL
        match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", remote_url)
        if not match:
            print(
                f"Error: Could not parse GitHub repo from remote URL: {remote_url}",
                file=sys.stderr,
            )
            sys.exit(1)

        owner, repo = match.groups()
        return owner, repo
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to get git remote URL: {e}", file=sys.stderr)
        sys.exit(1)


def trigger_workflow(
    owner: str, repo: str, max_todos: str, file_pattern: str
) -> int | None:
    """Trigger the TODO management workflow and return the run ID."""
    print(f"🚀 Triggering TODO management workflow in {owner}/{repo}")
    print(f"   Max TODOs: {max_todos}")
    if file_pattern:
        print(f"   File pattern: {file_pattern}")

    inputs = {"max_todos": max_todos}
    if file_pattern:
        inputs["file_pattern"] = file_pattern

    data = {
        "ref": "openhands/todo-management-example",  # Use our feature branch
        "inputs": inputs,
    }

    print("📋 Workflow dispatch payload:")
    print(f"   Branch: {data['ref']}")
    print(f"   Inputs: {json.dumps(inputs, indent=4)}")

    status_code, response = make_github_request(
        "POST",
        f"/repos/{owner}/{repo}/actions/workflows/todo-management.yml/dispatches",
        data,
    )

    if status_code == 204:
        print("✅ Workflow triggered successfully")
        # GitHub doesn't return the run ID in the dispatch response,
        # so we need to find it
        time.sleep(2)  # Wait a moment for the workflow to appear
        return get_latest_workflow_run(owner, repo)
    else:
        print(f"❌ Failed to trigger workflow (HTTP {status_code}): {response}")
        return None


def get_latest_workflow_run(owner: str, repo: str) -> int | None:
    """Get the latest workflow run ID for the TODO management workflow."""
    status_code, response = make_github_request(
        "GET",
        f"/repos/{owner}/{repo}/actions/workflows/todo-management.yml/runs?per_page=1",
    )

    if status_code == 200 and response.get("workflow_runs"):
        run_id = response["workflow_runs"][0]["id"]
        print(f"📋 Found workflow run ID: {run_id}")
        return run_id
    else:
        print(f"❌ Failed to get workflow runs (HTTP {status_code}): {response}")
        return None


def wait_for_workflow_completion(owner: str, repo: str, run_id: int) -> dict:
    """Wait for the workflow to complete and return the final status."""
    print(f"⏳ Waiting for workflow run {run_id} to complete...")

    while True:
        status_code, response = make_github_request(
            "GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}"
        )

        if status_code != 200:
            print(f"❌ Failed to get workflow status (HTTP {status_code}): {response}")
            return response

        status = response.get("status")
        conclusion = response.get("conclusion")

        print(f"   Status: {status}, Conclusion: {conclusion}")

        if status == "completed":
            print(f"✅ Workflow completed with conclusion: {conclusion}")
            return response

        time.sleep(10)  # Wait 10 seconds before checking again


def get_workflow_logs(owner: str, repo: str, run_id: int) -> None:
    """Download and display workflow logs."""
    print(f"📄 Fetching workflow logs for run {run_id}...")

    # Get jobs for this run
    status_code, response = make_github_request(
        "GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    )

    if status_code != 200:
        print(f"❌ Failed to get workflow jobs (HTTP {status_code}): {response}")
        return

    jobs = response.get("jobs", [])
    for job in jobs:
        job_id = job["id"]
        job_name = job["name"]
        job_conclusion = job.get("conclusion", "unknown")

        print(f"\n📋 Job: {job_name} (ID: {job_id}, Conclusion: {job_conclusion})")

        # Get logs for this job
        status_code, logs_response = make_github_request(
            "GET", f"/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
        )

        if status_code == 200:
            # The logs are returned as plain text, not JSON
            import subprocess

            cmd = [
                "curl",
                "-s",
                "-L",
                "-H",
                f"Authorization: token {os.getenv('GITHUB_TOKEN')}",
                "-H",
                "Accept: application/vnd.github.v3+json",
                f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job_id}/logs",
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                logs = result.stdout

                # Show last 50 lines of logs for each job
                log_lines = logs.split("\n")
                if len(log_lines) > 50:
                    print(f"   ... (showing last 50 lines of {len(log_lines)} total)")
                    log_lines = log_lines[-50:]

                for line in log_lines:
                    if line.strip():
                        print(f"   {line}")
            except subprocess.CalledProcessError:
                print(f"   ❌ Failed to fetch logs for job {job_name}")
        else:
            print(f"   ❌ Failed to get logs for job {job_name}")


def find_created_prs(owner: str, repo: str, run_id: int) -> list[str]:
    """Find PRs created by the workflow run."""
    print(f"🔍 Looking for PRs created by workflow run {run_id}...")

    # Look for recent PRs created by openhands-bot
    status_code, response = make_github_request(
        "GET",
        f"/repos/{owner}/{repo}/pulls?state=open&sort=created&direction=desc&per_page=10",
    )

    if status_code != 200:
        print(f"❌ Failed to get pull requests (HTTP {status_code}): {response}")
        return []

    prs = response.get("pulls", [])
    created_prs = []

    # Look for PRs created by openhands-bot in the last hour
    import datetime

    one_hour_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)

    for pr in prs:
        pr_created = datetime.datetime.fromisoformat(
            pr["created_at"].replace("Z", "+00:00")
        )
        pr_author = pr["user"]["login"]

        if pr_created > one_hour_ago and pr_author == "openhands-bot":
            created_prs.append(pr["html_url"])
            print(f"   📝 Found PR: {pr['html_url']}")
            print(f"      Title: {pr['title']}")
            print(f"      Created: {pr['created_at']}")

    return created_prs


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Debug the TODO management workflow")
    parser.add_argument(
        "--max-todos",
        default="3",
        help="Maximum number of TODOs to process (default: 3)",
    )
    parser.add_argument(
        "--file-pattern", default="", help="File pattern to scan (optional)"
    )

    args = parser.parse_args()

    print("🔧 TODO Management Workflow Debugger")
    print("=" * 50)

    # Get repository information
    owner, repo = get_repo_info()
    print(f"📁 Repository: {owner}/{repo}")

    # Trigger the workflow
    run_id = trigger_workflow(owner, repo, args.max_todos, args.file_pattern)
    if not run_id:
        print("❌ Failed to trigger workflow")
        sys.exit(1)

    # Wait for completion
    final_status = wait_for_workflow_completion(owner, repo, run_id)

    # Show logs
    get_workflow_logs(owner, repo, run_id)

    # Check results
    conclusion = final_status.get("conclusion")
    if conclusion == "success":
        print("\n🎉 Workflow completed successfully!")

        # Look for created PRs
        created_prs = find_created_prs(owner, repo, run_id)
        if created_prs:
            print(f"\n📝 Created PRs ({len(created_prs)}):")
            for pr_url in created_prs:
                print(f"   • {pr_url}")
        else:
            print("\n📝 No PRs were created (possibly no TODOs found)")

    elif conclusion == "failure":
        print("\n❌ Workflow failed!")
        print("Check the logs above for error details.")
        sys.exit(1)

    elif conclusion == "cancelled":
        print("\n⚠️ Workflow was cancelled")
        sys.exit(1)

    else:
        print(f"\n❓ Workflow completed with unknown conclusion: {conclusion}")
        sys.exit(1)


if __name__ == "__main__":
    main()
