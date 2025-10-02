"""Tests for PlanningAgent class."""

from unittest.mock import Mock

import pytest

from openhands.sdk.agent.planning import PlanningAgent
from openhands.sdk.llm import LLM


@pytest.fixture
def mock_llm():
    """Create a properly mocked LLM instance."""
    mock = Mock(spec=LLM)
    # Add all required attributes to avoid AttributeError during initialization
    mock.openrouter_site_url = None
    mock.openrouter_app_name = None
    mock.aws_access_key_id = None
    mock.aws_secret_access_key = None
    mock.aws_session_token = None
    mock.aws_region_name = None
    mock._metrics = None
    mock.model = "test-model"
    mock.log_completions = False
    mock.custom_tokenizer = None
    mock.base_url = "http://test.com"
    mock.reasoning_effort = None
    mock.model_copy.return_value = mock
    return mock


def test_planning_agent_initialization(mock_llm):
    """Test that PlanningAgent initializes with correct defaults."""

    agent = PlanningAgent(llm=mock_llm)

    # Verify it's a PlanningAgent instance
    assert isinstance(agent, PlanningAgent)

    # Verify default system prompt configuration
    assert agent.system_prompt_kwargs is not None
    assert agent.system_prompt_kwargs.get("planning_mode") is True
    assert agent.system_prompt_kwargs.get("read_only_mode") is True


def test_planning_agent_custom_system_prompt(mock_llm):
    """Test PlanningAgent with custom system prompt configuration."""
    custom_kwargs = {"custom_param": "value"}

    agent = PlanningAgent(llm=mock_llm, system_prompt_kwargs=custom_kwargs)

    # Verify custom kwargs are preserved and planning kwargs are added
    assert agent.system_prompt_kwargs["custom_param"] == "value"
    assert agent.system_prompt_kwargs["planning_mode"] is True
    assert agent.system_prompt_kwargs["read_only_mode"] is True


def test_planning_agent_system_prompt_filename(mock_llm):
    """Test that PlanningAgent uses correct system prompt filename."""

    agent = PlanningAgent(llm=mock_llm)

    # Should use planning-specific system prompt
    assert agent.system_prompt_filename == "planning_system_prompt.j2"


def test_planning_agent_custom_system_prompt_filename(mock_llm):
    """Test PlanningAgent with custom system prompt filename."""
    custom_filename = "custom_prompt.j2"

    agent = PlanningAgent(llm=mock_llm, system_prompt_filename=custom_filename)

    # Should use the custom filename
    assert agent.system_prompt_filename == custom_filename
