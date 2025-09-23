"""Tests for OpenAI Responses API support in LLM class."""

from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from openhands.sdk.llm import LLM


class TestResponsesAPI:
    """Test cases for the responses API functionality."""

    def test_responses_api_available_import(self):
        """Test that responses API imports are handled gracefully."""
        # This test ensures the import doesn't fail even if litellm doesn't have
        # responses API
        llm = LLM(model="gpt-3.5-turbo", api_key=SecretStr("test-key"))
        assert hasattr(llm, "responses")

    def test_responses_method_signature(self):
        """Test that the responses method has the correct signature."""
        llm = LLM(model="gpt-3.5-turbo", api_key=SecretStr("test-key"))

        # Check method exists and has correct parameters
        assert hasattr(llm, "responses")
        assert callable(llm.responses)

    @patch("openhands.sdk.llm.llm.RESPONSES_API_AVAILABLE", True)
    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_call_basic(self, mock_litellm_responses):
        """Test basic responses API call."""
        # Mock the response
        mock_response = Mock()
        mock_response.output = [Mock(content="Hello, World!", type="text")]
        mock_response.id = "test-response-id"
        mock_response.usage = Mock(total_tokens=10)
        mock_litellm_responses.return_value = mock_response

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        response = llm.responses(
            input_text="Hello, world!",
            instructions="You are a helpful assistant.",
            max_output_tokens=100,
        )

        # Verify the call was made
        mock_litellm_responses.assert_called_once()
        call_args = mock_litellm_responses.call_args[1]

        assert call_args["input"] == "Hello, world!"
        assert call_args["model"] == "gpt-5"
        assert call_args["instructions"] == "You are a helpful assistant."
        assert call_args["max_output_tokens"] == 100
        assert call_args["api_key"] == "test-key"

        # Verify response
        assert response == mock_response

    @patch("openhands.sdk.llm.llm.RESPONSES_API_AVAILABLE", True)
    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_with_tools(self, mock_litellm_responses):
        """Test responses API call with tools."""
        # Mock the response
        mock_response = Mock()
        mock_response.output = [Mock(content="Used tool", type="text")]
        mock_litellm_responses.return_value = mock_response

        # Mock tool
        mock_tool = Mock()
        mock_tool.to_openai_tool.return_value = {
            "type": "function",
            "function": {"name": "test_tool"},
        }

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        llm.responses(input_text="Use the tool", tools=[mock_tool])

        # Verify the call was made with tools
        mock_litellm_responses.assert_called_once()
        call_args = mock_litellm_responses.call_args[1]

        assert call_args["tools"] == [
            {"type": "function", "function": {"name": "test_tool"}}
        ]
        mock_tool.to_openai_tool.assert_called_once()

    @patch("openhands.sdk.llm.llm.RESPONSES_API_AVAILABLE", True)
    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_temperature_handling(self, mock_litellm_responses):
        """Test that temperature is handled correctly for different models."""
        # Mock the response
        mock_response = Mock()
        mock_response.output = [Mock(content="Response", type="text")]
        mock_litellm_responses.return_value = mock_response

        # Test with GPT-5 (default temperature 0.0 should not be passed)
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        llm.responses(input_text="Test")

        call_args = mock_litellm_responses.call_args[1]
        assert "temperature" not in call_args

        # Test with explicit temperature
        mock_litellm_responses.reset_mock()
        llm.responses(input_text="Test", temperature=0.7)

        call_args = mock_litellm_responses.call_args[1]
        assert call_args["temperature"] == 0.7

    @patch("openhands.sdk.llm.llm.RESPONSES_API_AVAILABLE", False)
    def test_responses_api_not_available(self):
        """Test error when responses API is not available."""
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        with pytest.raises(ValueError, match="Responses API is not available"):
            llm.responses(input_text="Test")

    @patch("openhands.sdk.llm.llm.RESPONSES_API_AVAILABLE", True)
    def test_responses_api_streaming_not_supported(self):
        """Test that streaming raises an error."""
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        with pytest.raises(ValueError, match="Streaming is not supported"):
            llm.responses(input_text="Test", stream=True)

    @patch("openhands.sdk.llm.llm.RESPONSES_API_AVAILABLE", True)
    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_empty_response_error(self, mock_litellm_responses):
        """Test error handling for empty responses."""
        from openhands.sdk.llm.llm import LLMNoResponseError

        # Mock empty response
        mock_litellm_responses.return_value = None

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        with pytest.raises(LLMNoResponseError, match="Response is empty"):
            llm.responses(input_text="Test")

    @patch("openhands.sdk.llm.llm.RESPONSES_API_AVAILABLE", True)
    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_parameter_filtering(self, mock_litellm_responses):
        """Test that None parameters are filtered out."""
        # Mock the response
        mock_response = Mock()
        mock_response.output = [Mock(content="Response", type="text")]
        mock_litellm_responses.return_value = mock_response

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        llm.responses(
            input_text="Test",
            tools=None,
            instructions=None,
            max_output_tokens=None,
            temperature=None,
        )

        call_args = mock_litellm_responses.call_args[1]

        # None values should be filtered out
        assert "tools" not in call_args
        assert "instructions" not in call_args
        assert "temperature" not in call_args
        # max_output_tokens should use default from LLM instance
        assert "max_output_tokens" in call_args
