"""Tests for the LLMSecurityAnalyzer class."""

import pytest

from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.tool.schema import Schema, SchemaField, SchemaInstance
from openhands.sdk.tool.schema.types import SchemaFieldType


ACTION_SCHEMA = Schema(
    name="tests.securityAnalyzer.action",
    fields=[
        SchemaField(
            name="command",
            description="Command to execute",
            type=SchemaFieldType.from_type(str),
            required=True,
        ),
        SchemaField(
            name="security_risk",
            description="LLM-provided security risk",
            type=SchemaFieldType.from_type(str),
            required=False,
            default=SecurityRisk.UNKNOWN.value,
        ),
    ],
)


def create_mock_action(
    command: str = "test_command", risk: SecurityRisk = SecurityRisk.UNKNOWN
) -> SchemaInstance:
    return SchemaInstance(
        name="testAction",
        definition=ACTION_SCHEMA,
        data={"command": command, "security_risk": risk.value},
    )


@pytest.mark.parametrize(
    "risk_level",
    [
        SecurityRisk.UNKNOWN,
        SecurityRisk.LOW,
        SecurityRisk.MEDIUM,
        SecurityRisk.HIGH,
    ],
)
def test_llm_security_analyzer_returns_stored_risk(risk_level: SecurityRisk):
    """Test that LLMSecurityAnalyzer returns the security_risk stored in the action."""
    analyzer = LLMSecurityAnalyzer()
    action = create_mock_action(command="test", risk=risk_level)

    result = analyzer.security_risk(action)

    assert result == risk_level
