"""Tests for OpenAI Responses API support in LLM class."""

from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from openhands.sdk.llm import LLM, Message, TextContent


class TestResponsesAPI:
    """Test cases for the responses API functionality."""

    def test_use_responses_auto_detection_gpt5(self):
        """Test that use_responses is automatically set to True for GPT-5 models."""
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))
        assert llm.use_responses is True

    def test_use_responses_auto_detection_gpt5_codex(self):
        """Test that use_responses is automatically set to True for GPT-5-codex."""
        llm = LLM(model="openai/gpt-5-codex", api_key=SecretStr("test-key"))
        assert llm.use_responses is True

    def test_use_responses_auto_detection_other_models(self):
        """Test that use_responses is automatically set to False for non-GPT-5."""
        llm = LLM(model="gpt-4", api_key=SecretStr("test-key"))
        assert llm.use_responses is False

    def test_use_responses_explicit_override(self):
        """Test that explicit use_responses setting overrides auto-detection."""
        # Force responses API for non-GPT-5 model
        llm = LLM(model="gpt-4", api_key=SecretStr("test-key"), use_responses=True)
        assert llm.use_responses is True

        # Force completion API for GPT-5 model
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"), use_responses=False)
        assert llm.use_responses is False

    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_method_signature(self, mock_responses):
        """Test that the responses method has the correct signature."""
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        # Check method exists and has correct parameters
        assert hasattr(llm, "responses")
        assert callable(llm.responses)

    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_call_basic(self, mock_responses):
        """Test basic responses API call."""
        # Mock the responses API response
        mock_response = Mock()
        mock_response.output = "Hello, World!"
        mock_responses.return_value = mock_response

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        llm.responses(
            input_text="Say hello", instructions="You are a helpful assistant"
        )

        # Verify the call was made
        mock_responses.assert_called_once()
        call_args = mock_responses.call_args
        assert call_args[1]["input"] == "Say hello"
        assert call_args[1]["instructions"] == "You are a helpful assistant"
        assert call_args[1]["model"] == "gpt-5"

    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_with_tools(self, mock_responses):
        """Test responses API call with tools."""
        from openhands.sdk.tool import Tool

        # Mock the responses API response
        mock_response = Mock()
        mock_response.output = "I'll use the calculator tool."
        mock_responses.return_value = mock_response

        # Create a mock tool
        mock_tool = Mock(spec=Tool)
        mock_tool.to_openai_tool.return_value = {
            "type": "function",
            "function": {"name": "calculator", "description": "A calculator tool"},
        }

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        llm.responses(input_text="Calculate 2+2", tools=[mock_tool])

        # Verify the call was made with tools
        mock_responses.assert_called_once()
        call_args = mock_responses.call_args
        assert "tools" in call_args[1]

    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_temperature_handling(self, mock_responses):
        """Test that temperature parameter is passed to responses API."""  # noqa: E501
        # Mock the responses API response
        mock_response = Mock()
        mock_response.output = "Response"
        mock_responses.return_value = mock_response

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        # Call with temperature - should be passed to responses API
        llm.responses(input_text="Test", temperature=0.7)

        # Verify temperature was passed to responses API
        mock_responses.assert_called_once()
        call_args = mock_responses.call_args
        assert call_args[1]["temperature"] == 0.7

    def test_responses_api_streaming_not_supported(self):
        """Test that streaming raises an error in responses API."""
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        with pytest.raises(ValueError, match="Streaming is not supported"):
            llm.responses(input_text="Test", stream=True)

    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_empty_response_error(self, mock_responses):
        """Test that empty response raises an error."""
        # Mock empty response
        mock_response = Mock()
        mock_response.output = None
        mock_responses.return_value = mock_response

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        with pytest.raises(Exception):  # Should raise LLMNoResponseError
            llm.responses(input_text="Test")

    @patch("openhands.sdk.llm.llm.litellm_responses")
    def test_responses_api_parameter_passing(self, mock_responses):
        """Test that parameters are passed to responses API."""
        # Mock the responses API response
        mock_response = Mock()
        mock_response.output = "Response"
        mock_responses.return_value = mock_response

        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        llm.responses(
            input_text="Test",
            max_output_tokens=100,
            custom_param="custom_value",
        )

        # Verify parameters were passed
        mock_responses.assert_called_once()
        call_args = mock_responses.call_args
        assert call_args[1]["max_output_tokens"] == 100
        assert call_args[1]["custom_param"] == "custom_value"

    @patch("openhands.sdk.llm.llm.litellm_completion")
    def test_completion_uses_responses_api_for_gpt5(self, mock_completion):
        """Test that completion method uses responses API for GPT-5 models."""
        llm = LLM(model="gpt-5", api_key=SecretStr("test-key"))

        # Mock the _call_responses_api method
        with patch.object(llm, "_call_responses_api") as mock_call_responses:
            from litellm.types.utils import ModelResponse

            # Create a proper ModelResponse object
            mock_response = ModelResponse(
                id="test-id",
                choices=[{"message": {"content": "test"}}],
                created=1234567890,
                model="gpt-5",
                object="chat.completion",
            )
            mock_call_responses.return_value = mock_response

            llm.completion(
                messages=[Message(role="user", content=[TextContent(text="Hello")])]
            )

            # Verify responses API was called, not completion API
            mock_call_responses.assert_called_once()
            mock_completion.assert_not_called()

    @patch("openhands.sdk.llm.llm.litellm_completion")
    def test_completion_uses_completion_api_for_gpt4(self, mock_completion):
        """Test that completion method uses completion API for non-GPT-5 models."""
        from litellm.types.utils import ModelResponse

        # Mock completion API response
        mock_response = ModelResponse(
            id="test-id",
            choices=[{"message": {"content": "test"}}],
            created=1234567890,
            model="gpt-4",
            object="chat.completion",
        )
        mock_completion.return_value = mock_response

        llm = LLM(model="gpt-4", api_key=SecretStr("test-key"))

        llm.completion(
            messages=[Message(role="user", content=[TextContent(text="Hello")])]
        )

        # Verify completion API was called
        mock_completion.assert_called_once()
