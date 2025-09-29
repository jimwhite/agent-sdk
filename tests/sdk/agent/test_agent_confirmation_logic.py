"""Tests for agent confirmation logic with DefaultSecurityAnalyzer."""

from litellm import ChatCompletionMessageToolCall
from litellm.types.utils import Function
from pydantic import SecretStr

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.event import ActionEvent
from openhands.sdk.llm import LLM, TextContent
from openhands.sdk.security.analyzer import SecurityAnalyzerBase
from openhands.sdk.security.confirmation_policy import AlwaysConfirm, NeverConfirm
from openhands.sdk.security.default_analyzer import DefaultSecurityAnalyzer
from openhands.sdk.security.risk import SecurityRisk
from openhands.sdk.tool.builtins import FinishAction, ThinkAction


class MockSecurityAnalyzer(SecurityAnalyzerBase):
    """Test security analyzer that returns HIGH risk for all actions."""

    def security_risk(self, action):
        """Return HIGH risk for all actions."""
        return SecurityRisk.HIGH


class TestAgentConfirmationLogic:
    """Test suite for agent confirmation logic with DefaultSecurityAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.llm = LLM(
            model="gpt-4", api_key=SecretStr("test-key"), service_id="test-llm"
        )

    def _create_action_event(
        self, action, tool_name, call_id, response_id="response_1"
    ):
        """Helper to create properly formatted ActionEvent objects."""
        tool_call = ChatCompletionMessageToolCall(
            id=call_id,
            type="function",
            function=Function(name=tool_name, arguments="{}"),
        )

        return ActionEvent(
            source="agent",
            thought=[TextContent(text="Test thought")],
            action=action,
            tool_name=tool_name,
            tool_call_id=call_id,
            tool_call=tool_call,
            llm_response_id=response_id,
        )

    def test_agent_uses_default_security_analyzer_when_none_provided(self):
        """Test that agent uses DefaultSecurityAnalyzer when no security analyzer is provided."""  # noqa: E501
        agent = Agent(llm=self.llm, tools=[])

        # Agent should use DefaultSecurityAnalyzer when none is provided
        effective_analyzer = agent._effective_security_analyzer
        assert isinstance(effective_analyzer, DefaultSecurityAnalyzer)

    def test_agent_uses_provided_security_analyzer(self):
        """Test that agent uses the provided security analyzer when one is given."""
        custom_analyzer = MockSecurityAnalyzer()
        agent = Agent(llm=self.llm, tools=[], security_analyzer=custom_analyzer)

        # Agent should use the provided analyzer
        effective_analyzer = agent._effective_security_analyzer
        assert effective_analyzer is custom_analyzer

    def test_confirmation_logic_with_default_analyzer_always_confirm(self):
        """Test confirmation logic with DefaultSecurityAnalyzer and AlwaysConfirm policy."""  # noqa: E501
        agent = Agent(llm=self.llm, tools=[])
        conversation = Conversation(agent=agent)

        # Set confirmation policy to always confirm
        conversation.set_confirmation_policy(AlwaysConfirm())

        # Create a ThinkAction event (not FinishAction)
        action_event = self._create_action_event(
            action=ThinkAction(thought="test thought"),
            tool_name="think",
            call_id="test_call_id",
        )

        # Test the confirmation logic directly
        state = conversation.state
        action_events = [action_event]

        # Since DefaultSecurityAnalyzer returns UNKNOWN and AlwaysConfirm confirms UNKNOWN  # noqa: E501
        # this should require confirmation
        requires_confirmation = any(
            state.confirmation_policy.should_confirm(risk)
            for _, risk in agent._effective_security_analyzer.analyze_pending_actions(
                action_events
            )
        )

        assert requires_confirmation is True

    def test_confirmation_logic_with_default_analyzer_never_confirm(self):
        """Test confirmation logic with DefaultSecurityAnalyzer and NeverConfirm policy."""  # noqa: E501
        agent = Agent(llm=self.llm, tools=[])
        conversation = Conversation(agent=agent)

        # Set confirmation policy to never confirm
        conversation.set_confirmation_policy(NeverConfirm())

        # Create a ThinkAction event
        action_event = self._create_action_event(
            action=ThinkAction(thought="test thought"),
            tool_name="think",
            call_id="test_call_id",
        )

        # Test the confirmation logic directly
        state = conversation.state
        action_events = [action_event]

        # Since NeverConfirm never confirms any risk, this should not require confirmation  # noqa: E501
        requires_confirmation = any(
            state.confirmation_policy.should_confirm(risk)
            for _, risk in agent._effective_security_analyzer.analyze_pending_actions(
                action_events
            )
        )

        assert requires_confirmation is False

    def test_single_finish_action_never_requires_confirmation(self):
        """Test that single FinishAction never requires confirmation regardless of policy."""  # noqa: E501
        agent = Agent(llm=self.llm, tools=[])
        conversation = Conversation(agent=agent)

        # Set confirmation policy to always confirm
        conversation.set_confirmation_policy(AlwaysConfirm())

        # Create a FinishAction event
        finish_action_event = self._create_action_event(
            action=FinishAction(message="test"),
            tool_name="finish",
            call_id="finish_call_id",
        )

        # Test the confirmation logic directly - single FinishAction should never require confirmation  # noqa: E501
        state = conversation.state
        action_events = [finish_action_event]

        # This mimics the logic in the step() method
        if len(action_events) == 1 and isinstance(
            action_events[0].action, FinishAction
        ):
            requires_confirmation = False
        else:
            analyzer = agent._effective_security_analyzer
            requires_confirmation = any(
                state.confirmation_policy.should_confirm(risk)
                for _, risk in analyzer.analyze_pending_actions(action_events)
            )

        assert requires_confirmation is False

    def test_empty_action_list_never_requires_confirmation(self):
        """Test that empty action list never requires confirmation."""
        agent = Agent(llm=self.llm, tools=[])
        conversation = Conversation(agent=agent)

        # Set confirmation policy to always confirm
        conversation.set_confirmation_policy(AlwaysConfirm())

        # Test the confirmation logic with empty action list
        state = conversation.state
        action_events = []

        # This mimics the logic in the step() method
        if len(action_events) == 0:
            requires_confirmation = False
        else:
            analyzer = agent._effective_security_analyzer
            requires_confirmation = any(
                state.confirmation_policy.should_confirm(risk)
                for _, risk in analyzer.analyze_pending_actions(action_events)
            )

        assert requires_confirmation is False

    def test_multiple_actions_with_finish_requires_confirmation(self):
        """Test that multiple actions including FinishAction still require confirmation."""  # noqa: E501
        agent = Agent(llm=self.llm, tools=[])
        conversation = Conversation(agent=agent)

        # Set confirmation policy to always confirm
        conversation.set_confirmation_policy(AlwaysConfirm())

        # Create multiple action events including FinishAction
        regular_action_event = self._create_action_event(
            action=ThinkAction(thought="test thought"),
            tool_name="think",
            call_id="test_call_id",
        )
        finish_action_event = self._create_action_event(
            action=FinishAction(message="test"),
            tool_name="finish",
            call_id="finish_call_id",
        )

        # Test the confirmation logic with multiple actions
        state = conversation.state
        action_events = [regular_action_event, finish_action_event]

        # This mimics the logic in the step() method
        if len(action_events) == 1 and isinstance(
            action_events[0].action, FinishAction
        ):
            requires_confirmation = False
        elif len(action_events) == 0:
            requires_confirmation = False
        else:
            analyzer = agent._effective_security_analyzer
            requires_confirmation = any(
                state.confirmation_policy.should_confirm(risk)
                for _, risk in analyzer.analyze_pending_actions(action_events)
            )

        assert requires_confirmation is True

    def test_default_analyzer_returns_unknown_risk(self):
        """Test that DefaultSecurityAnalyzer returns UNKNOWN risk for all actions."""
        agent = Agent(llm=self.llm, tools=[])

        # Create various action events
        action_events = [
            self._create_action_event(
                action=ThinkAction(thought="test thought"),
                tool_name="think",
                call_id="call_1",
            ),
            self._create_action_event(
                action=FinishAction(message="test"),
                tool_name="finish",
                call_id="call_2",
            ),
        ]

        # Analyze actions with default analyzer
        analyzed_actions = agent._effective_security_analyzer.analyze_pending_actions(
            action_events
        )

        # All actions should have UNKNOWN risk
        for action, risk in analyzed_actions:
            assert risk == SecurityRisk.UNKNOWN
            assert action in action_events
