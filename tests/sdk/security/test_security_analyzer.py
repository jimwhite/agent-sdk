"""Tests for the SecurityAnalyzer class."""

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function

from openhands.sdk.event import ActionEvent
from openhands.sdk.llm import TextContent
from openhands.sdk.security.analyzer import PerActionSecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.tool import ActionBase


# TODO: Serialization tests for implementers of the base classes


class TestSecurityAnalyzerBase:
    """Test suite for SecurityAnalyzerBase."""


class TestPerActionSecurityAnalyzer:
    """Test suite for PerActionSecurityAnalyzer."""

    def test_independent_of_current_context(self) -> None:
        """Test that PerActionSecurityAnalyzer is independent of current_context.

        That is, we should get the same results regardless of what current_context is.
        """

    def test_handles_actions_independently(self):
        """Test that PerActionSecurityAnalyzer handles each action independently.

        Regardless of the number of actions or how they are batched, we should get the
        same result per-action.
        """

    def test_analyzes_all_pending_actions(self):
        """Test that PerActionSecurityAnalyzer analyzes all pending actions."""

    def test_handles_exceptions_with_unknown(self):
        """Test that PerActionSecurityAnalyzer handles exceptions by returning UNKNOWN
        risk.
        """

    def test_handles_empty_pending_actions_input(self):
        """Test that PerActionSecurityAnalyzer handles empty pending actions list."""


class TestSecurityAnalyzerMockAction(ActionBase):
    """Mock action for testing."""

    command: str = "test_command"


class TestSecurityAnalyzer(PerActionSecurityAnalyzer):
    """Test implementation of SecurityAnalyzer with controllable security_risk
    method.
    """

    risk_return_value: SecurityRisk = SecurityRisk.LOW
    security_risk_calls: list[ActionEvent] = []

    def security_risk(self, action: ActionEvent) -> SecurityRisk:
        """Return configurable risk level for testing."""
        self.security_risk_calls.append(action)
        return self.risk_return_value


def create_mock_action_event(action: ActionBase) -> ActionEvent:
    """Helper to create ActionEvent for testing."""
    return ActionEvent(
        thought=[TextContent(text="test thought")],
        action=action,
        tool_name="test_tool",
        tool_call_id="test_call_id",
        tool_call=ChatCompletionMessageToolCall(
            id="test_call_id",
            function=Function(name="test_tool", arguments='{"command": "test"}'),
            type="function",
        ),
        llm_response_id="test_response_id",
    )


def test_analyze_event_with_action_event():
    """Test analyze_event with ActionEvent returns security risk."""
    analyzer = TestSecurityAnalyzer(risk_return_value=SecurityRisk.MEDIUM)
    action = TestSecurityAnalyzerMockAction(command="test")
    action_event = create_mock_action_event(action)

    result = analyzer.security_risk(action_event)

    assert result == SecurityRisk.MEDIUM
    assert len(analyzer.security_risk_calls) == 1
    assert analyzer.security_risk_calls[0] == action_event


def test_analyze_pending_actions_success():
    """Test analyze_pending_actions with successful analysis."""
    analyzer = TestSecurityAnalyzer(risk_return_value=SecurityRisk.MEDIUM)

    action1 = TestSecurityAnalyzerMockAction(command="action1")
    action2 = TestSecurityAnalyzerMockAction(command="action2")
    action_event1 = create_mock_action_event(action1)
    action_event2 = create_mock_action_event(action2)

    pending_actions = [action_event1, action_event2]

    result = analyzer.analyze_pending_actions([], pending_actions)

    assert len(result) == 2

    risks = list(result.values())

    assert risks[0] == SecurityRisk.MEDIUM
    assert risks[1] == SecurityRisk.MEDIUM
    assert len(analyzer.security_risk_calls) == 2


def test_analyze_pending_actions_empty_list():
    """Test analyze_pending_actions with empty list."""
    analyzer = TestSecurityAnalyzer(risk_return_value=SecurityRisk.LOW)

    result = analyzer.analyze_pending_actions([], [])
    assert result == []
    assert len(analyzer.security_risk_calls) == 0


def test_analyze_pending_actions_with_exception():
    """Test analyze_pending_actions handles exceptions by defaulting to HIGH risk."""

    class FailingAnalyzer(TestSecurityAnalyzer):
        def security_risk(self, action: ActionEvent) -> SecurityRisk:
            super().security_risk(action)  # Record the call
            raise ValueError("Analysis failed")

    analyzer = FailingAnalyzer()
    action = TestSecurityAnalyzerMockAction(command="failing_action")
    action_event = create_mock_action_event(action)

    result = analyzer.analyze_pending_actions([], [action_event])

    assert len(result) == 1

    risks = list(result.values())

    assert risks[0] == SecurityRisk.HIGH
    assert len(analyzer.security_risk_calls) == 1


def test_analyze_pending_actions_mixed_risks() -> None:
    """Test analyze_pending_actions with different risk levels."""

    class VariableRiskAnalyzer(TestSecurityAnalyzer):
        call_count: int = 0
        risks: list[SecurityRisk] = [
            SecurityRisk.LOW,
            SecurityRisk.HIGH,
            SecurityRisk.MEDIUM,
        ]

        def security_risk(self, action: ActionEvent) -> SecurityRisk:
            risk = self.risks[self.call_count % len(self.risks)]
            self.call_count += 1
            return risk

    analyzer = VariableRiskAnalyzer()

    actions = [TestSecurityAnalyzerMockAction(command=f"action{i}") for i in range(3)]
    action_events = [create_mock_action_event(action) for action in actions]

    result = analyzer.analyze_pending_actions([], action_events)

    assert len(result) == 3

    risks = list(result.values())

    assert risks[0] == SecurityRisk.LOW
    assert risks[1] == SecurityRisk.HIGH
    assert risks[2] == SecurityRisk.MEDIUM


def test_analyze_pending_actions_partial_failure():
    """Test analyze_pending_actions with some actions failing analysis."""

    class PartiallyFailingAnalyzer(TestSecurityAnalyzer):
        def security_risk(self, action: ActionEvent) -> SecurityRisk:
            # In general not needed, but the test security analyzer is also recording
            # all the calls for testing purposes and this ensures we keep that behavior
            super().security_risk(action)

            assert hasattr(action.action, "command")
            if getattr(action.action, "command") == "failing_action":
                raise RuntimeError("Specific action failed")
            return SecurityRisk.LOW

    analyzer = PartiallyFailingAnalyzer()

    action1 = TestSecurityAnalyzerMockAction(command="good_action")
    action2 = TestSecurityAnalyzerMockAction(command="failing_action")
    action3 = TestSecurityAnalyzerMockAction(command="another_good_action")

    action_events = [
        create_mock_action_event(action1),
        create_mock_action_event(action2),
        create_mock_action_event(action3),
    ]

    result = analyzer.analyze_pending_actions([], action_events)

    assert len(result) == 3

    risks = list(result.values())

    assert risks[0] == SecurityRisk.LOW
    assert risks[1] == SecurityRisk.HIGH  # Failed analysis defaults to HIGH
    assert risks[2] == SecurityRisk.LOW
    assert len(analyzer.security_risk_calls) == 3
