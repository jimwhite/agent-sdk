"""Integration tests for configurable security policy functionality."""

import shutil
import tempfile
from pathlib import Path

import pytest
from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.llm import LLM


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def test_llm():
    """Create a test LLM instance."""
    return LLM(
        model="gpt-4o-mini",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )


@pytest.fixture
def custom_policy_content():
    """Sample custom security policy content."""
    return (
        "# 🔐 Custom Security Risk Policy\n"
        "When using tools that support the security_risk parameter, "
        "assess the safety risk of your actions:\n"
        "\n"
        "- **LOW**: Safe read-only actions.\n"
        "  - Viewing files, calculations, documentation.\n"
        "- **MEDIUM**: Moderate container-scoped actions.\n"
        "  - File modifications, package installations.\n"
        "- **HIGH**: Potentially dangerous actions.\n"
        "  - Network access, system modifications, data exfiltration.\n"
        "\n"
        "**Custom Rules**\n"
        "- Always prioritize user data safety.\n"
        "- Escalate to **HIGH** for any external data transmission."
    )


def test_default_security_policy_filename(test_llm):
    """Test that Agent uses default security policy filename."""
    agent = Agent(llm=test_llm)
    assert agent.security_policy_filename == "security_policy.j2"


def test_custom_security_policy_filename(test_llm):
    """Test that Agent accepts custom security policy filename."""
    agent = Agent(
        llm=test_llm,
        security_policy_filename="custom_policy.j2",
    )
    assert agent.security_policy_filename == "custom_policy.j2"


def test_security_policy_filename_in_system_message(
    temp_dir, custom_policy_content, test_llm, monkeypatch
):
    """Test that custom security policy filename is passed to system message template."""  # noqa: E501
    # Create a custom policy file
    custom_policy_path = Path(temp_dir) / "custom_policy.j2"
    custom_policy_path.write_text(custom_policy_content)

    # Create agent with custom security policy
    agent = Agent(
        llm=test_llm,
        security_policy_filename="custom_policy.j2",
    )

    # Mock the prompt_dir property to point to our temp directory
    original_prompt_dir = agent.prompt_dir

    def mock_prompt_dir(self):
        return temp_dir

    monkeypatch.setattr(Agent, "prompt_dir", property(mock_prompt_dir))

    # Copy the system_prompt.j2 to temp directory
    system_prompt_path = Path(temp_dir) / "system_prompt.j2"
    original_system_prompt = Path(original_prompt_dir) / "system_prompt.j2"
    if original_system_prompt.exists():
        shutil.copy2(original_system_prompt, system_prompt_path)
    else:
        # Create a minimal system prompt for testing
        system_prompt_path.write_text(
            "Test system prompt\n<SECURITY_RISK_ASSESSMENT>\n"
            "{% include security_policy_filename %}\n</SECURITY_RISK_ASSESSMENT>"
        )

    # Get system message - this should include our custom policy
    system_message = agent.system_message

    # Verify that custom policy content appears in system message
    assert "Custom Security Risk Policy" in system_message
    assert "Always prioritize user data safety" in system_message


def test_configurable_security_policy_filename(test_llm, monkeypatch):
    """Test that security_policy_filename can be configured and is used in template rendering."""  # noqa: E501
    # Copy example custom policy to test directory for this test
    example_dir = (
        Path(__file__).parent.parent.parent.parent / "examples" / "20_security_policy"
    )
    if not example_dir.exists():
        pytest.skip("Example directory not found")

    example_policy = example_dir / "custom_policy.j2"
    if not example_policy.exists():
        pytest.skip("Example custom policy not found")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the example policy to our test directory
        test_policy_path = Path(temp_dir) / "custom_policy.j2"
        shutil.copy2(example_policy, test_policy_path)

        # Create agent with custom security policy
        agent = Agent(
            llm=test_llm,
            security_policy_filename="custom_policy.j2",
        )

        # Mock the prompt_dir property to point to our temp directory
        original_prompt_dir = agent.prompt_dir

        def mock_prompt_dir(self):
            return temp_dir

        monkeypatch.setattr(Agent, "prompt_dir", property(mock_prompt_dir))

        # Copy the system_prompt.j2 to temp directory
        system_prompt_path = Path(temp_dir) / "system_prompt.j2"
        original_system_prompt = Path(original_prompt_dir) / "system_prompt.j2"
        if original_system_prompt.exists():
            shutil.copy2(original_system_prompt, system_prompt_path)

        # Get system message - this should include our custom policy
        system_message = agent.system_message

        # Verify that the custom policy content is included
        # The exact content will depend on what's in the example custom_policy.j2
        assert "SECURITY_RISK_ASSESSMENT" in system_message


def test_security_policy_filename_validation(test_llm):
    """Test that security_policy_filename field accepts valid string values."""
    # Test with various valid filenames
    valid_filenames = [
        "security_policy.j2",
        "custom_security_policy.j2",
        "my_policy.j2",
        "policy_v2.j2",
    ]

    for filename in valid_filenames:
        agent = Agent(
            llm=test_llm,
            security_policy_filename=filename,
        )
        assert agent.security_policy_filename == filename
