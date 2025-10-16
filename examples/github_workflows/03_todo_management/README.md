# Automated TODO Management with GitHub Actions

This example demonstrates how to use the OpenHands SDK to automatically scan a codebase for `# TODO(openhands)` comments and create pull requests to implement them. This showcases practical automation and self-improving codebase capabilities.

## Overview

The workflow consists of four main components:

1. **Scanner** (`scanner.py`) - Scans the codebase for TODO(openhands) comments
2. **Agent** (`agent.py`) - Uses OpenHands to implement individual TODOs
3. **GitHub Actions Workflow** (`workflow.yml`) - Orchestrates the automation
4. **Debug Tool** (`debug_workflow.py`) - Local testing and workflow debugging

## Features

- 🔍 **Smart Scanning**: Finds legitimate TODO(openhands) comments while filtering out false positives
- 🤖 **AI Implementation**: Uses OpenHands agent to automatically implement TODOs
- 🔄 **PR Management**: Creates feature branches and pull requests automatically
- 📝 **Progress Tracking**: Updates TODO comments with PR URLs
- 🐛 **Debug Support**: Comprehensive logging and local testing tools
- ⚙️ **Configurable**: Customizable limits and file patterns

## How It Works

1. **Scan Phase**: The workflow scans your codebase for `# TODO(openhands)` comments
   - Filters out false positives (documentation, test files, quoted strings)
   - Supports Python, TypeScript, and Java files
   - Provides detailed logging of found TODOs

2. **Process Phase**: For each TODO found:
   - Creates a feature branch
   - Uses OpenHands agent to implement the TODO
   - Creates a pull request with the implementation
   - Updates the original TODO comment with the PR URL

3. **Update Phase**: Original TODO comments are updated:
   ```python
   # Before
   # TODO(openhands): Add input validation
   
   # After (when PR is created)
   # TODO(in progress: https://github.com/owner/repo/pull/123): Add input validation
   ```

## Files

- **`workflow.yml`**: GitHub Actions workflow file
- **`scanner.py`**: Smart TODO scanner with false positive filtering
- **`agent.py`**: OpenHands agent for TODO implementation
- **`prompt.py`**: Contains the prompt template for TODO implementation
- **`debug_workflow.py`**: Debug script to trigger and monitor the workflow
- **`test_local.py`**: Local component testing script
- **`README.md`**: This comprehensive documentation

## Setup

### 1. Repository Secrets

Add these secrets to your GitHub repository:

- `LLM_API_KEY` - Your LLM API key (required)
- `GITHUB_TOKEN` - GitHub token with repo permissions (automatically provided)

### 2. Install Workflow

Copy `workflow.yml` to `.github/workflows/todo-management.yml` in your repository.

### 3. Configure Permissions

Ensure your `GITHUB_TOKEN` has these permissions:
- `contents: write`
- `pull-requests: write`
- `issues: write`
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

### Debug Script

For testing and debugging, use the provided debug script:

```bash
# Basic usage (processes up to 3 TODOs)
python debug_workflow.py

# Process only 1 TODO for testing
python debug_workflow.py --max-todos 1

# Scan specific file pattern
python debug_workflow.py --file-pattern "*.py"
```

The debug script will:
1. Trigger the workflow on GitHub
2. Wait for it to complete (blocking)
3. Show detailed logs from all jobs
4. Report any errors or list URLs of created PRs

**Requirements**: Set `GITHUB_TOKEN` environment variable with a GitHub token that has workflow permissions.

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

## Local Testing and Debugging

### Quick Component Test

```bash
# Test the scanner
python scanner.py /path/to/your/code

# Test all components
python test_local.py
```

### Full Workflow Debug

```bash
# Debug the complete workflow (requires GitHub token)
python debug_workflow.py --max-todos 1

# With file pattern filtering
python debug_workflow.py --max-todos 2 --file-pattern "*.py"

# Monitor workflow execution
python debug_workflow.py --max-todos 1 --monitor
```

The debug tool provides:
- 🚀 Workflow triggering via GitHub API
- 📊 Real-time monitoring of workflow runs
- 🔍 Detailed logging and error reporting
- ⏱️ Execution time tracking

## Smart Filtering

The scanner intelligently filters out false positives:

- ❌ Documentation strings and comments
- ❌ Test files and mock data
- ❌ Quoted strings containing TODO references
- ❌ Code that references TODO(openhands) but isn't a TODO
- ✅ Legitimate TODO comments in source code

## Troubleshooting

### Common Issues

1. **No TODOs found**: 
   - Ensure you're using the correct format `TODO(openhands)`
   - Check that TODOs aren't in test files or documentation
   - Use `python scanner.py .` to test locally

2. **Permission denied**: 
   - Check that `GITHUB_TOKEN` has required permissions
   - Verify repository settings allow Actions to create PRs

3. **LLM API errors**: 
   - Verify your `LLM_API_KEY` is correct and has sufficient credits
   - Check the model name is supported

4. **Workflow not found**:
   - Ensure workflow file is in `.github/workflows/`
   - Workflow must be on the main branch to be triggered

### Debug Mode

The workflow includes comprehensive logging. Check the workflow run logs for detailed information about:
- TODOs found during scanning
- Agent execution progress
- PR creation status
- Error messages and stack traces

## Limitations

- Processes a maximum number of TODOs per run to avoid overwhelming the system
- Requires LLM API access for the OpenHands agent
- GitHub Actions usage limits apply
- Agent implementation quality depends on TODO description clarity

## Contributing

To improve this example:

1. **Test locally**: Use `test_local.py` and `debug_workflow.py`
2. **Add file type support**: Extend scanner for new languages
3. **Improve filtering**: Enhance false positive detection
4. **Better prompts**: Improve agent implementation quality

### Development Workflow

```bash
# 1. Make changes to components
# 2. Test locally
python test_local.py

# 3. Test with debug tool
python debug_workflow.py --max-todos 1

# 4. Update documentation
# 5. Submit pull request
```

## Related Examples

- `01_basic_action` - Basic GitHub Actions integration
- `02_pr_review` - Automated PR review workflow

This example builds on the patterns established in `01_basic_action` while adding sophisticated TODO detection and automated implementation capabilities.

