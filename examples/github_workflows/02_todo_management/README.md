# Automated TODO Management with OpenHands

This example demonstrates how to set up automated TODO management using the OpenHands agent SDK and GitHub Actions. The system automatically scans your codebase for `# TODO(openhands)` comments and creates pull requests to implement them.

## Overview

The automated TODO management system consists of three main components:

1. **TODO Scanner** (`todo_scanner.py`): Scans the codebase for `# TODO(openhands)` comments
2. **TODO Agent** (`todo_agent.py`): Uses OpenHands to implement individual TODOs
3. **GitHub Workflow** (`workflow.yml`): Orchestrates the entire process

## How It Works

1. **Scan Phase**: The workflow scans your repository for `# TODO(openhands)` comments
2. **Implementation Phase**: For each TODO found:
   - Uses OpenHands agent to implement the TODO (agent handles branch creation and PR)
3. **Update Phase**: Updates the original TODO comment with the PR URL (e.g., `# TODO(in progress: https://github.com/owner/repo/pull/123)`)

## Files

- **`workflow.yml`**: GitHub Actions workflow file
- **`todo_scanner.py`**: Python script to scan for TODO comments (Python, TypeScript, Java only)
- **`todo_agent.py`**: Python script that implements individual TODOs using OpenHands
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

## Best Practices

### Writing Good TODO Comments

1. **Be Specific**: Include clear descriptions of what needs to be implemented
   ```python
   # Good
   # TODO(openhands): Add input validation to check email format and domain
   
   # Less helpful
   # TODO(openhands): Fix this function
   ```

2. **Provide Context**: Include relevant details about the expected behavior
   ```python
   # TODO(openhands): Implement retry logic with exponential backoff (max 3 retries)
   def api_request(url):
       return requests.get(url)
   ```

3. **Consider Scope**: Keep TODOs focused on single, implementable tasks
   ```python
   # Good - focused task
   # TODO(openhands): Add logging for failed authentication attempts
   
   # Too broad
   # TODO(openhands): Rewrite entire authentication system
   ```

### Repository Organization

1. **Limit Concurrent TODOs**: The workflow processes a maximum of 3 TODOs by default to avoid overwhelming your repository with PRs

2. **Review Process**: Set up branch protection rules to require reviews for TODO implementation PRs

3. **Testing**: Ensure your repository has good test coverage so the agent can verify implementations

## Troubleshooting

### Common Issues

1. **No TODOs Found**
   - Ensure TODO comments use the exact format: `# TODO(openhands)`
   - Check that files aren't in ignored directories (`.git`, `node_modules`, etc.)

2. **Agent Implementation Fails**
   - Check the workflow logs for specific error messages
   - Ensure the TODO description is clear and implementable
   - Verify the LLM API key is valid and has sufficient credits

3. **PR Creation Fails**
   - Ensure `GITHUB_TOKEN` has proper permissions
   - Check that the repository allows PR creation from workflows
   - Verify branch protection rules don't prevent automated commits

4. **Git Operations Fail**
   - Ensure the workflow has `contents: write` permission
   - Check for merge conflicts or repository state issues

### Debugging

1. **Check Artifacts**: The workflow uploads logs and scan results as artifacts
2. **Review PR Descriptions**: Failed implementations often include error details in PR descriptions
3. **Manual Testing**: Test the scripts locally before running in CI

## Local Testing

You can test the components locally before setting up the workflow:

### Test TODO Scanner

```bash
# Install dependencies
pip install -r requirements.txt  # if you have one

# Scan current directory
python examples/github_workflows/02_todo_management/todo_scanner.py .

# Scan specific directory
python examples/github_workflows/02_todo_management/todo_scanner.py src/

# Output to file
python examples/github_workflows/02_todo_management/todo_scanner.py . --output todos.json
```

### Test TODO Agent

```bash
# Set environment variables
export LLM_API_KEY="your-api-key"
export GITHUB_TOKEN="your-github-token"
export GITHUB_REPOSITORY="owner/repo"

# Create test TODO JSON
echo '{"file": "test.py", "line": 1, "content": "# TODO(openhands): Add hello world function", "description": "Add hello world function", "context": {"before": [], "after": []}}' > test_todo.json

# Process the TODO
python examples/github_workflows/02_todo_management/todo_agent.py "$(cat test_todo.json)"
```

## Customization

### Custom File Patterns

To scan only specific files or directories, you can modify the scanner or use workflow inputs:

```yaml
# In workflow dispatch
file_pattern: "src/**/*.py"  # Only Python files in src/
```

### Custom Prompts

The TODO agent generates prompts automatically, but you can modify `todo_agent.py` to customize the prompt generation logic.

### Integration with Other Tools

The workflow can be extended to integrate with:
- Code quality tools (linting, formatting)
- Testing frameworks
- Documentation generators
- Issue tracking systems

## Security Considerations

1. **API Keys**: Store LLM API keys in GitHub secrets, never in code
2. **Permissions**: Use minimal required permissions for the workflow
3. **Code Review**: Always review generated code before merging
4. **Rate Limits**: The workflow limits concurrent TODO processing to avoid API rate limits

## Limitations

1. **Context Understanding**: The agent works with local context around the TODO comment
2. **Complex Changes**: Very large or architectural changes may not be suitable for automated implementation
3. **Testing**: The agent may not always generate comprehensive tests
4. **Dependencies**: New dependencies may need manual approval

## Contributing

To improve this example:

1. Test with different types of TODO comments
2. Add support for more programming languages
3. Enhance error handling and recovery
4. Improve the prompt generation for better implementations

## References

- [OpenHands SDK Documentation](https://docs.all-hands.dev/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [LLM Provider Setup](https://docs.all-hands.dev/openhands/usage/llms/openhands-llms)
- [Basic Action Example](../01_basic_action/README.md)