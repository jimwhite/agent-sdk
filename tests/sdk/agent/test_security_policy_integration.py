"""Test configurable security policy functionality."""

import shutil
import tempfile
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.llm import LLM


def test_security_policy_in_system_message():
    """Test that security policy is included in system message."""
    agent = Agent(
        llm=LLM(
            model="test-model", api_key=SecretStr("test-key"), base_url="http://test"
        )
    )
    system_message = agent.system_message

    # Verify that security policy section is present
    assert "<SECURITY_RISK_ASSESSMENT>" in system_message
    assert "Security Risk Policy" in system_message


def test_custom_security_policy_in_system_message():
    """Test that custom security policy filename is used in system message."""
    # Create a temporary directory for test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a custom policy file with distinctive content
        custom_policy_path = Path(temp_dir) / "custom_policy.j2"
        custom_policy_content = (
            "# 🔐 Custom Test Security Policy\n"
            "This is a custom security policy for testing.\n"
            "- **CUSTOM_RULE**: Always test custom policies."
        )
        custom_policy_path.write_text(custom_policy_content)

        # Copy required template files to temp directory
        system_prompt_path = Path(temp_dir) / "system_prompt.j2"
        original_prompt_dir = (
            Path(__file__).parent.parent.parent.parent
            / "openhands"
            / "sdk"
            / "agent"
            / "prompts"
        )
        original_system_prompt = original_prompt_dir / "system_prompt.j2"
        shutil.copy2(original_system_prompt, system_prompt_path)

        security_risk_assessment_path = Path(temp_dir) / "security_risk_assessment.j2"
        original_security_risk_assessment = (
            original_prompt_dir / "security_risk_assessment.j2"
        )
        shutil.copy2(original_security_risk_assessment, security_risk_assessment_path)

        # Create agent with custom security policy using absolute paths for both
        agent = Agent(
            llm=LLM(
                model="test-model",
                api_key=SecretStr("test-key"),
                base_url="http://test",
            ),
            system_prompt_filename=str(system_prompt_path),
            security_policy_filename=str(custom_policy_path),
        )

        # Get system message - this should include our custom policy
        system_message = agent.system_message

        # Verify that custom policy content appears in system message
        assert "Custom Test Security Policy" in system_message
        assert "CUSTOM_RULE" in system_message
        assert "Always test custom policies" in system_message
