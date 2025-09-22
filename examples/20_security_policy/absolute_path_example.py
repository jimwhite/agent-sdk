#!/usr/bin/env python3
"""
Example demonstrating absolute path support for security policy templates.

This example shows how to use security policy templates located anywhere
on the filesystem, not just within the prompt directory.
"""

import tempfile
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import LLM, Agent


def main():
    """Demonstrate absolute path support for security policy templates."""
    # Create a temporary directory for our custom security policy
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a custom security policy in a temporary location
        custom_policy_path = Path(temp_dir) / "enterprise_security_policy.j2"
        custom_policy_content = """# 🔐 Enterprise Security Policy

This security policy is loaded from an absolute path outside the prompt directory.

## Security Requirements

- **DATA_PROTECTION**: All sensitive data must be encrypted at rest and in transit
- **ACCESS_CONTROL**: Implement role-based access control for all operations
- **AUDIT_LOGGING**: Log all security-relevant events for compliance
- **INCIDENT_RESPONSE**: Follow established procedures for security incidents

## Compliance Standards

This policy ensures compliance with:
- SOC 2 Type II
- ISO 27001
- GDPR requirements

## Implementation Notes

When using absolute paths, you can:
1. Store security policies in a centralized location
2. Share policies across multiple applications
3. Version control policies separately from application code
4. Implement policy management workflows
"""

        # Write the custom policy to the temporary file
        custom_policy_path.write_text(custom_policy_content)

        print(f"Created custom security policy at: {custom_policy_path}")

        # Create an agent using the absolute path to the security policy
        agent = Agent(
            llm=LLM(
                model="gpt-4",
                api_key=SecretStr("your-api-key-here"),
                base_url="https://api.openai.com/v1",
            ),
            security_policy_filename=str(custom_policy_path),  # Use absolute path
        )

        # Get the system message to see the custom policy in action
        system_message = agent.system_message

        print("\n" + "=" * 80)
        print("SYSTEM MESSAGE WITH CUSTOM SECURITY POLICY")
        print("=" * 80)
        print(system_message)
        print("=" * 80)

        # Verify that our custom policy content is included
        if "Enterprise Security Policy" in system_message:
            print("\n✅ SUCCESS: Custom security policy loaded from absolute path!")
        else:
            print("\n❌ ERROR: Custom security policy not found in system message")

        if "DATA_PROTECTION" in system_message:
            print("✅ SUCCESS: Custom policy content is present")
        else:
            print("❌ ERROR: Custom policy content not found")


if __name__ == "__main__":
    main()
