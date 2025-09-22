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


def test_absolute_path_security_policy():
    """Test that absolute path security policy files work."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a custom policy file with distinctive content
        custom_policy_path = Path(temp_dir) / "absolute_path_policy.j2"
        custom_policy_content = (
            "# 🔐 Absolute Path Security Policy\n"
            "This policy is loaded from an absolute path.\n"
            "- **ABSOLUTE_RULE**: Test absolute path loading."
        )
        custom_policy_path.write_text(custom_policy_content)

        # Create agent with absolute path to security policy
        agent = Agent(
            llm=LLM(
                model="test-model",
                api_key=SecretStr("test-key"),
                base_url="http://test",
            ),
            security_policy_filename=str(custom_policy_path),
        )

        # Get system message - this should include our custom policy
        system_message = agent.system_message

        # Verify that custom policy content appears in system message
        assert "Absolute Path Security Policy" in system_message
        assert "ABSOLUTE_RULE" in system_message
        assert "absolute path loading" in system_message


def test_absolute_path_system_prompt():
    """Test that absolute path system prompt files work."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a custom system prompt with distinctive content
        custom_system_prompt_path = Path(temp_dir) / "custom_system.j2"
        custom_system_prompt_content = (
            "You are a custom agent loaded from an absolute path.\n"
            "CUSTOM_MARKER: This is a test system prompt.\n"
            "<SECURITY>\n"
            "{% include security_policy_filename %}\n"
            "</SECURITY>"
        )
        custom_system_prompt_path.write_text(custom_system_prompt_content)

        # Create a security policy file in the same directory
        security_policy_path = Path(temp_dir) / "test_security.j2"
        security_policy_content = "# Test Security Policy\nThis is a test policy."
        security_policy_path.write_text(security_policy_content)

        # Create agent with absolute paths for both system prompt and security policy
        agent = Agent(
            llm=LLM(
                model="test-model",
                api_key=SecretStr("test-key"),
                base_url="http://test",
            ),
            system_prompt_filename=str(custom_system_prompt_path),
            security_policy_filename=str(security_policy_path),
        )

        # Get system message
        system_message = agent.system_message

        # Verify that both custom templates are used
        assert "custom agent loaded from an absolute path" in system_message
        assert "CUSTOM_MARKER" in system_message
        assert "Test Security Policy" in system_message
        assert "This is a test policy" in system_message
