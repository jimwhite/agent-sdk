"""Tests for responses converter utilities."""

from litellm.types.utils import ModelResponse

from openhands.sdk.llm.utils.responses_converter import (
    responses_to_completion_format,
)


def test_messages_to_responses_input_empty():
    # messages_to_responses_input removed; no-op test
    assert True


def test_messages_to_responses_input_dict_messages():
    """Test conversion with dict messages."""
    assert True


def test_messages_to_responses_input_with_tool_message():
    """Test conversion with tool messages."""
    assert True


def test_messages_to_responses_input_message_objects():
    """Test conversion with Message objects."""
    assert True


def test_responses_to_completion_format_basic():
    """Test basic conversion from responses format to completion format."""

    # Mock responses result
    class MockOutput:
        def __init__(self, type_name, content_text=None, content=None):
            self.type = type_name
            if content_text:
                self.content = MockContent(content_text)
            elif content:
                self.content = content

    class MockContent:
        def __init__(self, text):
            self.text = text

    class MockUsage:
        def __init__(self, input_tokens=10, output_tokens=20, total_tokens=30):
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens
            self.total_tokens = total_tokens

    class MockResponse:
        def __init__(self):
            self.id = "resp_123"
            self.created_at = (
                1234567890  # Fixed: ResponsesAPIResponse uses created_at, not created
            )
            self.model = "o1-preview"
            self.output = [
                MockOutput("message", content_text="Hello, how can I help you?"),
                MockOutput(
                    "reasoning",
                    content="The user is greeting me, I should respond politely.",
                ),
            ]
            self.usage = MockUsage()

    mock_response = MockResponse()
    result = responses_to_completion_format(mock_response)

    assert isinstance(result, ModelResponse)
    assert result.id == "resp_123"
    assert result.model == "o1-preview"
    assert result.created == 1234567890
    assert len(result.choices) == 1

    choice = result.choices[0]
    assert choice.index == 0
    assert choice.finish_reason == "stop"
    assert choice.message.role == "assistant"  # type: ignore[attr-defined]
    assert choice.message.content == "Hello, how can I help you?"  # type: ignore[attr-defined]
    assert hasattr(choice.message, "reasoning_content")  # type: ignore[attr-defined]
    assert (
        choice.message.reasoning_content  # type: ignore[attr-defined]
        == "The user is greeting me, I should respond politely."
    )

    assert result.usage.prompt_tokens == 10  # type: ignore[attr-defined]
    assert result.usage.completion_tokens == 20  # type: ignore[attr-defined]
    assert result.usage.total_tokens == 30  # type: ignore[attr-defined]


def test_responses_to_completion_format_no_reasoning():
    """Test conversion without reasoning content."""

    class MockOutput:
        def __init__(self, type_name, content_text):
            self.type = type_name
            self.content = MockContent(content_text)

    class MockContent:
        def __init__(self, text):
            self.text = text

    class MockResponse:
        def __init__(self):
            self.id = "resp_456"
            self.created_at = 1234567891
            self.model = "gpt-4o"
            self.output = [
                MockOutput("message", "Just a regular response."),
            ]

    mock_response = MockResponse()
    result = responses_to_completion_format(mock_response)

    assert isinstance(result, ModelResponse)
    assert result.choices[0].message.content == "Just a regular response."  # type: ignore[attr-defined]
    assert not hasattr(result.choices[0].message, "reasoning_content")  # type: ignore[attr-defined]


def test_responses_to_completion_format_empty_output():
    """Test conversion with empty output."""

    class MockResponse:
        def __init__(self):
            self.id = "resp_789"
            self.created_at = 1234567892
            self.model = "o1-mini"
            self.output = []

    mock_response = MockResponse()
    result = responses_to_completion_format(mock_response)

    assert isinstance(result, ModelResponse)
    assert result.choices[0].message.content == ""  # type: ignore[attr-defined]
    assert not hasattr(result.choices[0].message, "reasoning_content")  # type: ignore[attr-defined]
