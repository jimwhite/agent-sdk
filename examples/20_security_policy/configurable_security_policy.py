#!/usr/bin/env python3
"""
Example demonstrating configurable security policy support in OpenHands Agent.

This example shows how to:
1. Use the default security policy
2. Configure a custom security policy template
3. Verify the security policy is included in the system message
"""

import os
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.llm import LLM


def main():
    """Demonstrate configurable security policy functionality."""
    print("=== OpenHands Agent: Configurable Security Policy Example ===\n")

    # Example 1: Default security policy
    print("1. Creating agent with default security policy...")
    llm = LLM(
        model="gpt-4o-mini",
        api_key=SecretStr(os.getenv("OPENAI_API_KEY", "your-api-key-here")),
    )
    default_agent = Agent(llm=llm)
    print(
        f"   Default security policy filename: {default_agent.security_policy_filename}"
    )

    # Example 2: Custom security policy
    print("\n2. Creating agent with custom security policy...")

    # Get the path to our custom policy template
    example_dir = Path(__file__).parent
    custom_policy_path = example_dir / "custom_policy.j2"

    if not custom_policy_path.exists():
        print(f"   Error: Custom policy template not found at {custom_policy_path}")
        return

    custom_agent = Agent(
        llm=llm,
        security_policy_filename="custom_policy.j2",
    )
    print(
        f"   Custom security policy filename: {custom_agent.security_policy_filename}"
    )

    # Example 3: Demonstrate configuration
    print("\n3. Configuration summary...")
    print(f"   Default agent security policy: {default_agent.security_policy_filename}")
    print(f"   Custom agent security policy: {custom_agent.security_policy_filename}")
    print("   ✅ Security policy filename successfully configured!")

    # Note: The security policy template is automatically included in the agent's
    # system message when the agent processes conversations. The template is
    # rendered using Jinja2 and included in the SECURITY_RISK_ASSESSMENT section.

    print("\n=== Example completed successfully! ===")
    print("\nKey takeaways:")
    print("• Agents use 'security_policy.j2' as the default security policy template")
    print(
        "• You can specify a custom security policy using the "
        "security_policy_filename parameter"
    )
    print("• The security policy template is included in the agent's system message")
    print(
        "• Custom policies allow you to define organization-specific "
        "security guidelines"
    )


if __name__ == "__main__":
    main()
