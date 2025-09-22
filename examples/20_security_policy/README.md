# Security Policy Configuration Examples

This directory contains examples demonstrating how to configure custom security policies for OpenHands agents.

## Files

- `configurable_security_policy.py` - Shows how to use a custom security policy template
- `absolute_path_example.py` - Demonstrates using security policies from absolute paths
- `custom_policy.j2` - Example custom security policy template

## Usage

The security policy system allows you to customize the security guidelines that are included in the agent's system prompt. This is useful for:

- Implementing organization-specific security requirements
- Adding compliance guidelines
- Customizing security behavior for different environments
- Providing context-specific security instructions

## Configuration

You can specify a custom security policy by setting the `security_policy_filename` parameter when creating an agent:

### Using Relative Paths (within prompt directory)

```python
from openhands.sdk import Agent, LLM
from pydantic import SecretStr

agent = Agent(
    llm=LLM(
        model="gpt-4",
        api_key=SecretStr("your-api-key"),
        base_url="https://api.openai.com/v1",
    ),
    security_policy_filename="custom_security_policy.j2",  # Relative to prompt directory
)
```

### Using Absolute Paths (anywhere on filesystem)

```python
from openhands.sdk import Agent, LLM
from pydantic import SecretStr

agent = Agent(
    llm=LLM(
        model="gpt-4",
        api_key=SecretStr("your-api-key"),
        base_url="https://api.openai.com/v1",
    ),
    security_policy_filename="/path/to/enterprise_security_policy.j2",  # Absolute path
)
```

## Path Resolution

The system supports both relative and absolute paths:

- **Relative paths**: Looked up within the prompt directory (default behavior)
- **Absolute paths**: Used directly from the filesystem, allowing you to:
  - Store policies in centralized locations
  - Share policies across multiple applications
  - Version control policies separately from application code
  - Implement enterprise policy management workflows

The security policy template will be included in the system prompt using Jinja2 templating.

## Running the Examples

```bash
# Basic example with relative path
python configurable_security_policy.py

# Advanced example with absolute path
python absolute_path_example.py
```