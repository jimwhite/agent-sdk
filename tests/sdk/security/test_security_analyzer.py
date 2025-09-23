"""Tests for the SecurityAnalyzer class."""

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function

from openhands.sdk.event import ActionEvent
from openhands.sdk.event.base import LLMConvertibleEvent
from openhands.sdk.event.types import EventID
from openhands.sdk.llm import TextContent
from openhands.sdk.security.analyzer import PerActionSecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.tool import ActionBase


# TODO: Serialization tests for implementers of the base classes


class SimpleAction(ActionBase):
    """Simple action for testing."""

    command: str = "test_command"


def create_mock_action_event(command: str, security_risk: SecurityRisk) -> ActionEvent:
    """Helper to create ActionEvent for testing."""
    return ActionEvent(
        thought=[TextContent(text="test thought")],
        action=SimpleAction(command=command),
        tool_name="test_tool",
        tool_call_id="test_call_id",
        tool_call=ChatCompletionMessageToolCall(
            id="test_call_id",
            function=Function(name="test_tool", arguments='{"command": "test"}'),
            type="function",
        ),
        llm_response_id="test_response_id",
        security_risk=security_risk,
    )


class TestSecurityAnalyzerBase:
    """Test suite for SecurityAnalyzerBase."""


class TestPerActionSecurityAnalyzer:
    """Test suite for PerActionSecurityAnalyzer."""

    class FixedOutputAnalyzer(PerActionSecurityAnalyzer):
        risks: dict[EventID, SecurityRisk] = {}
        default_risk: SecurityRisk = SecurityRisk.UNKNOWN

        def security_risk(self, action: ActionEvent) -> SecurityRisk:
            return self.risks.get(action.id, self.default_risk)

        @staticmethod
        def from_actions(
            actions: list[ActionEvent],
            default_risk: SecurityRisk = SecurityRisk.UNKNOWN,
        ) -> "TestPerActionSecurityAnalyzer.FixedOutputAnalyzer":
            analyzer = TestPerActionSecurityAnalyzer.FixedOutputAnalyzer()
            analyzer.risks = {action.id: action.security_risk for action in actions}
            analyzer.default_risk = default_risk
            return analyzer

    def test_independent_of_current_context(self) -> None:
        """Test that PerActionSecurityAnalyzer is independent of current_context.

        That is, we should get the same results regardless of what current_context is.
        """
        possible_context: list[LLMConvertibleEvent] = []
        pending_actions: list[ActionEvent] = [
            create_mock_action_event("action_1", SecurityRisk.LOW),
            create_mock_action_event("action_2", SecurityRisk.HIGH),
            create_mock_action_event("action_3", SecurityRisk.MEDIUM),
        ]

        analyzer = self.FixedOutputAnalyzer.from_actions(pending_actions)

        result: dict[EventID, SecurityRisk] | None = None

        # Compute the security risks for all possible context prefixes.
        for context_size in range(len(possible_context)):
            context = possible_context[:context_size]
            current_result = analyzer.analyze_pending_actions(context, pending_actions)

            # If we haven't stored a result yet, do so. Otherwise, ensure it's the same
            # as what we've already seen.
            if result is None:
                result = current_result
            else:
                assert result == current_result

    def test_handles_actions_independently(self) -> None:
        """Test that PerActionSecurityAnalyzer handles each action independently.

        Regardless of the number of actions or how they are batched, we should get the
        same result per-action.
        """

        pending_actions: list[ActionEvent] = [
            create_mock_action_event("action_1", SecurityRisk.LOW),
            create_mock_action_event("action_2", SecurityRisk.HIGH),
            create_mock_action_event("action_3", SecurityRisk.MEDIUM),
        ]

        analyzer = self.FixedOutputAnalyzer.from_actions(pending_actions)

        risks = analyzer.analyze_pending_actions(
            current_context=[], pending_actions=pending_actions
        )

        for action in pending_actions:
            risk = analyzer.security_risk(action)
            assert risks[action.id] == risk

    def test_analyzes_all_pending_actions(self) -> None:
        """Test that PerActionSecurityAnalyzer analyzes all pending actions."""
        pending_actions: list[ActionEvent] = [
            create_mock_action_event("action_1", SecurityRisk.LOW),
            create_mock_action_event("action_2", SecurityRisk.HIGH),
            create_mock_action_event("action_3", SecurityRisk.MEDIUM),
        ]

        analyzer = self.FixedOutputAnalyzer.from_actions(pending_actions)

        result = analyzer.analyze_pending_actions(
            current_context=[], pending_actions=pending_actions
        )

        # Check that all actions have their IDs in the result
        assert all(action.id in result for action in pending_actions)

        # Check that all IDs in the result correspond to an action
        assert all(
            event_id in (action.id for action in pending_actions)
            for event_id in result.keys()
        )

    def test_handles_exceptions_with_unknown(self) -> None:
        """Test that PerActionSecurityAnalyzer handles exceptions by returning UNKNOWN
        risk.
        """

        class FailingAnalyzer(PerActionSecurityAnalyzer):
            # Regardless of the action, always raise an exception
            def security_risk(self, action: ActionEvent) -> SecurityRisk:
                raise ValueError("Analysis failed")

        pending_actions: list[ActionEvent] = []

        analyzer = FailingAnalyzer()

        # When analyzed independently, each action should return UNKNOWN risk
        for action in pending_actions:
            risk = analyzer.security_risk(action)
            assert risk == SecurityRisk.UNKNOWN

        # When analyzed in a batch, all actions should also return UNKNOWN risk
        risks = analyzer.analyze_pending_actions(
            current_context=[], pending_actions=pending_actions
        )
        assert all(risk == SecurityRisk.UNKNOWN for risk in risks.values())

    def test_handles_empty_pending_actions_input(self) -> None:
        """Test that PerActionSecurityAnalyzer handles empty pending actions list."""

        analyzer = self.FixedOutputAnalyzer()

        result = analyzer.analyze_pending_actions(
            current_context=[], pending_actions=[]
        )
        assert result == {}
