"""Test that the security policy is properly integrated into the agent system prompt."""

from unittest.mock import patch

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import (
    Choices,
    Function,
    Message as LiteLLMMessage,
    ModelResponse,
)
from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.event import ActionEvent, AgentErrorEvent
from openhands.sdk.llm import LLM, Message, TextContent
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer


def test_security_policy_in_system_message():
    """Test that the security policy is included in the agent's system message."""
    # Create a minimal agent configuration
    agent = Agent(
        llm=LLM(
            usage_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )

    # Get the system message
    system_message = agent.system_message

    # Verify that the security policy content is included
    assert "🔐 Security Policy" in system_message
    assert "OK to do without Explicit User Consent" in system_message
    assert "Do only with Explicit User Consent" in system_message
    assert "Never Do" in system_message

    # Verify specific policy items are present
    assert (
        "Download and run code from a repository specified by a user" in system_message
    )
    assert "Open pull requests on the original repositories" in system_message
    assert "Install and run popular packages from pypi, npm" in system_message
    assert (
        "Upload code to anywhere other than the location where it was obtained"
        in system_message
    )
    assert "Upload API keys or tokens anywhere" in system_message
    assert "Never perform any illegal activities" in system_message
    assert "Never run software to mine cryptocurrency" in system_message

    # Verify that all security guidelines are consolidated in the policy
    assert "General Security Guidelines" in system_message
    assert "Only use GITHUB_TOKEN and other credentials" in system_message
    assert "Use APIs to work with GitHub or other platforms" in system_message


def test_security_policy_template_rendering():
    """Test that the security policy template renders correctly."""

    from openhands.sdk.context.prompts.prompt import render_template

    # Get the prompts directory
    agent = Agent(
        llm=LLM(
            usage_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )
    prompt_dir = agent.prompt_dir

    # Render the security policy template
    security_policy = render_template(prompt_dir, "security_policy.j2")

    # Verify the content structure
    assert security_policy.startswith("# 🔐 Security Policy")
    assert "## OK to do without Explicit User Consent" in security_policy
    assert "## Do only with Explicit User Consent" in security_policy
    assert "## Never Do" in security_policy

    # Verify it's properly formatted (no extra whitespace at start/end)
    assert not security_policy.startswith(" ")
    assert not security_policy.endswith(" ")


def test_llm_security_analyzer_template_kwargs():
    """Test that agent sets template_kwargs appropriately when security analyzer is LLMSecurityAnalyzer."""  # noqa: E501
    # Create agent with LLMSecurityAnalyzer
    agent = Agent(
        llm=LLM(
            usage_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        ),
        security_analyzer=LLMSecurityAnalyzer(),
    )

    # Access the system_message property to trigger template_kwargs computation
    system_message = agent.system_message

    # Verify that the security risk assessment section is included in the system prompt
    assert "<SECURITY_RISK_ASSESSMENT>" in system_message
    assert "# Security Risk Policy" in system_message
    assert "When using tools that support the security_risk parameter" in system_message
    # By default, cli_mode is True, so we should see the CLI mode version
    assert "**LOW**: Safe, read-only actions" in system_message
    assert "**MEDIUM**: Project-scoped edits or execution" in system_message
    assert "**HIGH**: System-level or untrusted operations" in system_message
    assert "**Global Rules**" in system_message


def test_llm_security_analyzer_sandbox_mode():
    """Test that agent includes sandbox mode security risk assessment when cli_mode=False."""  # noqa: E501
    # Create agent with LLMSecurityAnalyzer and cli_mode=False
    agent = Agent(
        llm=LLM(
            usage_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        ),
        security_analyzer=LLMSecurityAnalyzer(),
        system_prompt_kwargs={"cli_mode": False},
    )

    # Access the system_message property to trigger template_kwargs computation
    system_message = agent.system_message

    # Verify that the security risk assessment section is included with sandbox mode content  # noqa: E501
    assert "<SECURITY_RISK_ASSESSMENT>" in system_message
    assert "# Security Risk Policy" in system_message
    assert "When using tools that support the security_risk parameter" in system_message
    # With cli_mode=False, we should see the sandbox mode version
    assert "**LOW**: Read-only actions inside sandbox" in system_message
    assert "**MEDIUM**: Container-scoped edits and installs" in system_message
    assert "**HIGH**: Data exfiltration or privilege breaks" in system_message
    assert "**Global Rules**" in system_message


def test_no_security_analyzer_excludes_risk_assessment():
    """Test that security risk assessment section is excluded when no security analyzer is set."""  # noqa: E501
    # Create agent without security analyzer
    agent = Agent(
        llm=LLM(
            usage_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )

    # Get the system message
    system_message = agent.system_message

    # Verify that the security risk assessment section is NOT included
    assert "<SECURITY_RISK_ASSESSMENT>" not in system_message
    assert "# Security Risk Policy" not in system_message
    assert (
        "When using tools that support the security_risk parameter"
        not in system_message
    )


def test_non_llm_security_analyzer_excludes_risk_assessment():
    """Test that security risk assessment section is excluded when security analyzer is not LLMSecurityAnalyzer."""  # noqa: E501
    from openhands.sdk.security.analyzer import SecurityAnalyzerBase
    from openhands.sdk.security.risk import SecurityRisk

    class MockSecurityAnalyzer(SecurityAnalyzerBase):
        def security_risk(self, action: ActionEvent) -> SecurityRisk:
            return SecurityRisk.LOW

    # Create agent with non-LLM security analyzer
    agent = Agent(
        llm=LLM(
            usage_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        ),
        security_analyzer=MockSecurityAnalyzer(),
    )

    # Get the system message
    system_message = agent.system_message

    # Verify that the security risk assessment section is NOT included
    assert "<SECURITY_RISK_ASSESSMENT>" not in system_message
    assert "# Security Risk Policy" not in system_message
    assert (
        "When using tools that support the security_risk parameter"
        not in system_message
    )


def _tool_response(name: str, args_json: str) -> ModelResponse:
    return ModelResponse(
        id="mock-response",
        choices=[
            Choices(
                index=0,
                message=LiteLLMMessage(
                    role="assistant",
                    content="tool call with security_risk",
                    tool_calls=[
                        ChatCompletionMessageToolCall(
                            id="call_1",
                            type="function",
                            function=Function(name=name, arguments=args_json),
                        )
                    ],
                ),
                finish_reason="tool_calls",
            )
        ],
        created=0,
        model="test-model",
        object="chat.completion",
    )


def test_security_risk_param_ignored_when_no_analyzer():
    """Security risk param is ignored when no analyzer is configured."""

    llm = LLM(
        usage_id="test-llm",
        model="test-model",
        api_key=SecretStr("test-key"),
        base_url="http://test",
    )
    agent = Agent(llm=llm, tools=[])

    events = []
    convo = Conversation(agent=agent, callbacks=[events.append])

    with patch(
        "openhands.sdk.llm.llm.litellm_completion",
        return_value=_tool_response(
            "think",
            '{"thought": "This is a test thought", "security_risk": "LOW"}',
        ),
    ):
        convo.send_message(
            Message(role="user", content=[TextContent(text="Please think")])
        )
        agent.step(convo.state, on_event=events.append)

    # No agent errors
    assert not any(isinstance(e, AgentErrorEvent) for e in events)
