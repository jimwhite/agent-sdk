"""Test configurable security policy functionality."""

import shutil
import tempfile
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.llm import LLM


def test_default_security_policy_filename():
    """Test that Agent uses default security policy filename."""
    agent = Agent(
        llm=LLM(
            model="test-model", api_key=SecretStr("test-key"), base_url="http://test"
        )
    )
    assert agent.security_policy_filename == "security_policy.j2"


def test_custom_security_policy_filename():
    """Test that Agent accepts custom security policy filename."""
    agent = Agent(
        llm=LLM(
            model="test-model", api_key=SecretStr("test-key"), base_url="http://test"
        ),
        security_policy_filename="custom_policy.j2",
    )
    assert agent.security_policy_filename == "custom_policy.j2"


def test_custom_security_policy_in_system_message(monkeypatch):
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

        # Create agent with custom security policy
        agent = Agent(
            llm=LLM(
                model="test-model",
                api_key=SecretStr("test-key"),
                base_url="http://test",
            ),
            security_policy_filename="custom_policy.j2",
        )

        # Mock the prompt_dir property to point to our temp directory
        original_prompt_dir = agent.prompt_dir

        def mock_prompt_dir(self):
            return temp_dir

        monkeypatch.setattr(Agent, "prompt_dir", property(mock_prompt_dir))

        # Copy required template files to temp directory
        system_prompt_path = Path(temp_dir) / "system_prompt.j2"
        original_system_prompt = Path(original_prompt_dir) / "system_prompt.j2"
        shutil.copy2(original_system_prompt, system_prompt_path)

        security_risk_assessment_path = Path(temp_dir) / "security_risk_assessment.j2"
        original_security_risk_assessment = (
            Path(original_prompt_dir) / "security_risk_assessment.j2"
        )
        shutil.copy2(original_security_risk_assessment, security_risk_assessment_path)

        # Get system message - this should include our custom policy
        system_message = agent.system_message

        # Verify that custom policy content appears in system message
        assert "Custom Test Security Policy" in system_message
        assert "CUSTOM_RULE" in system_message
        assert "Always test custom policies" in system_message
