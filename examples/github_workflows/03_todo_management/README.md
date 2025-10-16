# Automated TODO Management with OpenHands

This example demonstrates how to set up automated TODO management using the OpenHands agent SDK and GitHub Actions. The system automatically scans your codebase for `# TODO(openhands)` comments and creates pull requests to implement them.

## Overview

The automated TODO management system consists of three main components:

1. **TODO Scanner** (`scanner.py`): Scans the codebase for `# TODO(openhands)` comments
2. **TODO Agent** (`agent.py`): Uses OpenHands to implement individual TODOs
3. **GitHub Workflow** (`workflow.yml`): Orchestrates the entire process

## How It Works

1. **Scan Phase**: The workflow scans your repository for `# TODO(openhands)` comments
2. **Implementation Phase**: For each TODO found:
   - Uses OpenHands agent to implement the TODO (agent handles branch creation and PR)
3. **Update Phase**: Detects the feature branch created by the agent, finds the corresponding PR using GitHub API, then updates the original TODO comment with the PR URL (e.g., `# TODO(in progress: https://github.com/owner/repo/pull/123)`)

## Files

- **`workflow.yml`**: GitHub Actions workflow file
- **`scanner.py`**: Simple Python script to scan for TODO comments (Python, TypeScript, Java only)
- **`agent.py`**: Python script that implements individual TODOs using OpenHands
- **`prompt.py`**: Contains the prompt template for TODO implementation
- **`README.md`**: This documentation file

## Setup

### 1. Copy the workflow file

Copy `workflow.yml` to `.github/workflows/todo-management.yml` in your repository:

```bash
cp examples/github_workflows/02_todo_management/workflow.yml .github/workflows/todo-management.yml
```

### 2. Configure secrets

Set the following secrets in your GitHub repository settings:

- **`LLM_API_KEY`** (required): Your LLM API key
  - Get one from the [OpenHands LLM Provider](https://docs.all-hands.dev/openhands/usage/llms/openhands-llms)

### 3. Ensure proper permissions

The workflow requires the following permissions (already configured in the workflow file):
- `contents: write` - To create branches and commit changes
- `pull-requests: write` - To create pull requests
- `issues: write` - To create issues if needed

### 4. Add TODO comments to your code

Add TODO comments in the following format anywhere in your codebase:

```python
# TODO(openhands): Add input validation for user email
def process_user_email(email):
    return email.lower()

# TODO(openhands): Implement caching mechanism for API responses
def fetch_api_data(endpoint):
    # Current implementation without caching
    return requests.get(endpoint).json()
```

Supported comment styles:
- `# TODO(openhands): description` (Python, Shell, etc.)
- `// TODO(openhands): description` (JavaScript, C++, etc.)
- `/* TODO(openhands): description */` (CSS, C, etc.)
- `<!-- TODO(openhands): description -->` (HTML, XML, etc.)

## Usage

### Manual runs

1. Go to Actions → "Automated TODO Management"
2. Click "Run workflow"
3. (Optional) Configure parameters:
   - **Max TODOs**: Maximum number of TODOs to process (default: 3)
   - **File Pattern**: Specific files to scan (leave empty for all files)
4. Click "Run workflow"

### Scheduled runs

To enable automated scheduled runs, edit `.github/workflows/todo-management.yml` and uncomment the schedule section:

```yaml
on:
  schedule:
    # Run every Monday at 9 AM UTC
    - cron: "0 9 * * 1"
```

Customize the cron schedule as needed. See [Cron syntax reference](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule).

## Example Workflow

Here's what happens when the workflow runs:

1. **Scan**: Finds TODO comments like:
   ```python
   # TODO(openhands): Add error handling for network timeouts
   def api_call(url):
       return requests.get(url)
   ```

2. **Implementation**: Creates a feature branch and implements:
   ```python
   import requests
   from requests.exceptions import Timeout, RequestException
   
   def api_call(url, timeout=30):
       """Make API call with proper error handling for network timeouts."""
       try:
           response = requests.get(url, timeout=timeout)
           response.raise_for_status()
           return response
       except Timeout:
           raise TimeoutError(f"Request to {url} timed out after {timeout} seconds")
       except RequestException as e:
           raise ConnectionError(f"Failed to connect to {url}: {str(e)}")
   ```

3. **PR Creation**: Creates a pull request with:
   - Clear title: "Implement TODO in api_utils.py:15 - Add error handling for network timeouts"
   - Detailed description explaining the implementation
   - Link back to the original TODO

4. **Update**: Updates the original TODO:
   ```python
   # TODO(in progress: https://github.com/owner/repo/pull/123): Add error handling for network timeouts
   ```

## Configuration Options

### Workflow Inputs

- **`max_todos`**: Maximum number of TODOs to process in a single run (default: 3)
- **`file_pattern`**: File pattern to scan (future enhancement)

### Environment Variables

- **`LLM_MODEL`**: Language model to use (default: `openhands/claude-sonnet-4-5-20250929`)
- **`LLM_BASE_URL`**: Custom LLM API base URL (optional)

