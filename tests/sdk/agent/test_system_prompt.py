"""Test system prompt customization functionality."""

import json

from openhands.sdk.agent import Agent
from openhands.sdk.agent.base import AgentBase
from openhands.sdk.llm import LLM


def test_agent_default_system_prompt():
    """Test that agent uses template-based system prompt by default."""
    llm = LLM(model="test-model", service_id="test-llm")
    agent = Agent(llm=llm, tools=[])

    # Should use template-based system message
    system_message = agent.system_message
    assert isinstance(system_message, str)
    assert len(system_message) > 0
    # Should contain content from the default template
    assert "OpenHands agent" in system_message


def test_agent_custom_system_prompt():
    """Test that agent uses custom system prompt when provided."""
    custom_prompt = "You are a helpful AI assistant specialized in code review."
    llm = LLM(model="test-model", service_id="test-llm")
    agent = Agent(llm=llm, tools=[], system_prompt=custom_prompt)

    # Should use the custom system prompt
    system_message = agent.system_message
    assert system_message == custom_prompt


def test_agent_custom_system_prompt_with_agent_context():
    """Test that agent context suffix is applied to custom system prompt."""
    from openhands.sdk.context.agent_context import AgentContext

    custom_prompt = "You are a helpful AI assistant."
    suffix = "Always end responses with 'Have a great day!'"

    agent_context = AgentContext(system_message_suffix=suffix)
    llm = LLM(model="test-model", service_id="test-llm")
    agent = Agent(
        llm=llm, tools=[], system_prompt=custom_prompt, agent_context=agent_context
    )

    # Should use custom prompt with context suffix
    system_message = agent.system_message
    assert system_message == f"{custom_prompt}\n\n{suffix}"


def test_agent_system_prompt_serialization():
    """Test that custom system prompt is included in model_dump."""
    custom_prompt = "You are a helpful AI assistant specialized in code review."
    llm = LLM(model="test-model", service_id="test-llm")
    agent = Agent(llm=llm, tools=[], system_prompt=custom_prompt)

    # Should include system_prompt in serialization
    agent_dict = agent.model_dump()
    assert "system_prompt" in agent_dict
    assert agent_dict["system_prompt"] == custom_prompt


def test_agent_system_prompt_json_serialization():
    """Test that custom system prompt survives JSON serialization/deserialization."""
    custom_prompt = "You are a helpful AI assistant specialized in code review."
    llm = LLM(model="test-model", service_id="test-llm")
    agent = Agent(llm=llm, tools=[], system_prompt=custom_prompt)

    # Serialize to JSON
    agent_json = agent.model_dump_json()

    # Deserialize from JSON
    deserialized_agent = AgentBase.model_validate_json(agent_json)

    # Should preserve the custom system prompt
    assert isinstance(deserialized_agent, Agent)
    assert deserialized_agent.system_prompt == custom_prompt
    assert deserialized_agent.system_message == custom_prompt


def test_agent_system_prompt_none_serialization():
    """Test that None system_prompt is handled correctly in serialization."""
    llm = LLM(model="test-model", service_id="test-llm")
    agent = Agent(llm=llm, tools=[], system_prompt=None)

    # Should include system_prompt as None in serialization
    agent_dict = agent.model_dump()
    assert "system_prompt" in agent_dict
    assert agent_dict["system_prompt"] is None

    # Should use template-based system message
    system_message = agent.system_message
    assert isinstance(system_message, str)
    assert len(system_message) > 0


def test_agent_system_prompt_json_roundtrip():
    """Test that system prompt survives JSON roundtrip with dict parsing."""
    custom_prompt = "You are a helpful AI assistant specialized in code review."
    llm = LLM(model="test-model", service_id="test-llm")
    agent = Agent(llm=llm, tools=[], system_prompt=custom_prompt)

    # Serialize to JSON, then parse to dict
    agent_json = agent.model_dump_json()
    agent_dict = json.loads(agent_json)

    # Deserialize from dict
    deserialized_agent = AgentBase.model_validate(agent_dict)

    # Should preserve the custom system prompt
    assert isinstance(deserialized_agent, Agent)
    assert deserialized_agent.system_prompt == custom_prompt
    assert deserialized_agent.system_message == custom_prompt


def test_agent_system_prompt_overrides_template():
    """Test that custom system prompt completely overrides template-based generation."""
    custom_prompt = "Custom prompt without any template content."
    llm = LLM(model="test-model", service_id="test-llm")

    # Create agent with custom system prompt and template kwargs
    agent = Agent(
        llm=llm,
        tools=[],
        system_prompt=custom_prompt,
        system_prompt_kwargs={"cli_mode": True},  # This should be ignored
    )

    # Should use only the custom prompt, ignoring template kwargs
    system_message = agent.system_message
    assert system_message == custom_prompt
    # Should not contain any template content
    assert "OpenHands agent" not in system_message
