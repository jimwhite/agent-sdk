"""Test the refactored tool validation logic in agent.py."""

import json

from litellm.types.utils import ChatCompletionMessageToolCall, Function
from pydantic import SecretStr

from openhands.sdk import Conversation
from openhands.sdk.agent.agent import Agent
from openhands.sdk.event import AgentErrorEvent
from openhands.sdk.llm import LLM


def test_validate_tool_call_non_function_type():
    """Test that _validate_tool_call returns error for non-function tool calls."""
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )

    # Create a tool call with non-function type
    tool_call = ChatCompletionMessageToolCall(
        id="test-id",
        type="not_function",  # Invalid type
        function=Function(name="test_tool", arguments="{}"),
    )

    error = agent._validate_tool_call(tool_call)
    assert error is not None
    assert isinstance(error, AgentErrorEvent)
    assert "not of type 'function'" in error.error
    assert error.tool_name == "test_tool"
    assert error.tool_call_id == "test-id"


def test_validate_tool_call_missing_tool_name():
    """Test that _validate_tool_call returns error for tool calls without name."""
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )

    # Create a tool call with no function name
    tool_call = ChatCompletionMessageToolCall(
        id="test-id",
        type="function",
        function=Function(name=None, arguments="{}"),
    )

    error = agent._validate_tool_call(tool_call)
    assert error is not None
    assert isinstance(error, AgentErrorEvent)
    assert "Tool call must have a name" in error.error
    assert error.tool_name == "unknown"
    assert error.tool_call_id == "test-id"


def test_validate_tool_call_tool_not_found():
    """Test that _validate_tool_call returns error for non-existent tools."""
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )
    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Create a tool call for a tool that doesn't exist
    tool_call = ChatCompletionMessageToolCall(
        id="test-id",
        type="function",
        function=Function(name="nonexistent_tool", arguments="{}"),
    )

    error = agent._validate_tool_call(tool_call)
    assert error is not None
    assert isinstance(error, AgentErrorEvent)
    assert "Tool 'nonexistent_tool' not found" in error.error
    assert error.tool_name == "nonexistent_tool"
    assert error.tool_call_id == "test-id"


def test_validate_tool_call_invalid_arguments():
    """Test that _validate_tool_call returns error for invalid arguments."""
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )
    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Create a tool call with invalid JSON arguments
    tool_call = ChatCompletionMessageToolCall(
        id="test-id",
        type="function",
        function=Function(name="finish", arguments="invalid json"),
    )

    error = agent._validate_tool_call(tool_call)
    assert error is not None
    assert isinstance(error, AgentErrorEvent)
    assert "Error validating args" in error.error
    assert error.tool_name == "finish"
    assert error.tool_call_id == "test-id"


def test_validate_tool_call_valid_tool():
    """Test that _validate_tool_call returns None for valid tool calls."""
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )
    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Create a valid tool call for the finish tool
    tool_call = ChatCompletionMessageToolCall(
        id="test-id",
        type="function",
        function=Function(
            name="finish",
            arguments=json.dumps({"message": "Task completed successfully"}),
        ),
    )

    error = agent._validate_tool_call(tool_call)
    assert error is None


def test_validate_tool_call_with_security_risk():
    """Test that _validate_tool_call handles security_risk field correctly."""
    agent = Agent(
        llm=LLM(
            service_id="test-llm",
            model="test-model",
            api_key=SecretStr("test-key"),
            base_url="http://test",
        )
    )
    # Initialize the agent by creating a conversation
    Conversation(agent=agent, visualize=False)

    # Create a valid tool call with security_risk field
    tool_call = ChatCompletionMessageToolCall(
        id="test-id",
        type="function",
        function=Function(
            name="finish",
            arguments=json.dumps(
                {"message": "Task completed successfully", "security_risk": "LOW"}
            ),
        ),
    )

    error = agent._validate_tool_call(tool_call)
    assert error is None  # Should pass validation even with security_risk field
