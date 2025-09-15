"""Test for GPT-5-mini temperature issue with litellm_proxy.

This test reproduces the issue where GPT-5-mini requires temperature to be set to 1,
but the LLM class defaults to temperature=0.0, causing an error.
"""

from unittest.mock import patch

import pytest
from pydantic import SecretStr

from openhands.sdk.llm import LLM


@patch("openhands.sdk.llm.llm.litellm_completion")
def test_gpt5_mini_temperature_issue_without_temperature(mock_completion):
    """Test that GPT-5-mini fails when temperature is not explicitly set to 1.

    This test reproduces the issue where GPT-5-mini requires temperature=1
    but the LLM class defaults to temperature=0.0, causing an error.
    """

    # Mock the litellm completion to raise an error when temperature != 1
    # This simulates the actual behavior of GPT-5-mini
    def mock_completion_side_effect(*args, **kwargs):
        temperature = kwargs.get("temperature", 0.0)
        if temperature != 1.0:
            raise ValueError(
                "GPT-5-mini requires temperature to be set to 1.0, "
                f"but got temperature={temperature}"
            )
        # If temperature is 1.0, return a mock response
        from litellm.types.utils import Choices, Message, ModelResponse, Usage

        return ModelResponse(
            id="test-response",
            choices=[
                Choices(
                    finish_reason="stop",
                    index=0,
                    message=Message(
                        content="Test response from GPT-5-mini",
                        role="assistant",
                    ),
                )
            ],
            created=1234567890,
            model="gpt-5-mini",
            object="chat.completion",
            system_fingerprint="test",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            ),
        )

    mock_completion.side_effect = mock_completion_side_effect

    # Create LLM with litellm_proxy/openai/gpt-5-mini without specifying temperature
    # This should use the default temperature=0.0
    llm = LLM(
        model="litellm_proxy/openai/gpt-5-mini",
        api_key=SecretStr("test_key"),
        num_retries=1,  # Reduce retries for faster test
        retry_min_wait=1,
        retry_max_wait=2,
    )

    # Verify that the LLM has the default temperature of 0.0
    assert llm.temperature == 0.0

    # Try to use the completion API - this should fail
    messages = [{"role": "user", "content": "Hello, GPT-5-mini!"}]

    with pytest.raises(
        ValueError, match="GPT-5-mini requires temperature to be set to 1.0"
    ):
        llm.completion(messages=messages)

    # Verify that the mock was called with temperature=0.0
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs.get("temperature") == 0.0


@patch("openhands.sdk.llm.llm.litellm_completion")
def test_gpt5_mini_works_with_temperature_1(mock_completion):
    """Test that GPT-5-mini works when temperature is explicitly set to 1.

    This test shows that the issue can be resolved by explicitly setting temperature=1.
    """

    # Mock the litellm completion to work when temperature == 1
    def mock_completion_side_effect(*args, **kwargs):
        temperature = kwargs.get("temperature", 0.0)
        if temperature != 1.0:
            raise ValueError(
                "GPT-5-mini requires temperature to be set to 1.0, "
                f"but got temperature={temperature}"
            )
        # If temperature is 1.0, return a mock response
        from litellm.types.utils import Choices, Message, ModelResponse, Usage

        return ModelResponse(
            id="test-response",
            choices=[
                Choices(
                    finish_reason="stop",
                    index=0,
                    message=Message(
                        content="Test response from GPT-5-mini",
                        role="assistant",
                    ),
                )
            ],
            created=1234567890,
            model="gpt-5-mini",
            object="chat.completion",
            system_fingerprint="test",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            ),
        )

    mock_completion.side_effect = mock_completion_side_effect

    # Create LLM with litellm_proxy/openai/gpt-5-mini with temperature=1.0
    llm = LLM(
        model="litellm_proxy/openai/gpt-5-mini",
        api_key=SecretStr("test_key"),
        temperature=1.0,  # Explicitly set temperature to 1.0
        num_retries=1,
        retry_min_wait=1,
        retry_max_wait=2,
    )

    # Verify that the LLM has temperature set to 1.0
    assert llm.temperature == 1.0

    # Try to use the completion API - this should work
    messages = [{"role": "user", "content": "Hello, GPT-5-mini!"}]

    response = llm.completion(messages=messages)

    # Verify the response
    assert response is not None
    assert response.choices[0].message.content == "Test response from GPT-5-mini"  # type: ignore

    # Verify that the mock was called with temperature=1.0
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs.get("temperature") == 1.0


@patch("openhands.sdk.llm.llm.litellm_completion")
def test_gpt5_mini_temperature_override_in_completion_call(mock_completion):
    """Test that temperature can be overridden in the completion call.

    This test shows that even if the LLM has a default temperature,
    it can be overridden in the completion call.
    """

    # Mock the litellm completion to work when temperature == 1
    def mock_completion_side_effect(*args, **kwargs):
        temperature = kwargs.get("temperature", 0.0)
        if temperature != 1.0:
            raise ValueError(
                "GPT-5-mini requires temperature to be set to 1.0, "
                f"but got temperature={temperature}"
            )
        # If temperature is 1.0, return a mock response
        from litellm.types.utils import Choices, Message, ModelResponse, Usage

        return ModelResponse(
            id="test-response",
            choices=[
                Choices(
                    finish_reason="stop",
                    index=0,
                    message=Message(
                        content="Test response from GPT-5-mini",
                        role="assistant",
                    ),
                )
            ],
            created=1234567890,
            model="gpt-5-mini",
            object="chat.completion",
            system_fingerprint="test",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            ),
        )

    mock_completion.side_effect = mock_completion_side_effect

    # Create LLM with litellm_proxy/openai/gpt-5-mini with default temperature=0.0
    llm = LLM(
        model="litellm_proxy/openai/gpt-5-mini",
        api_key=SecretStr("test_key"),
        num_retries=1,
        retry_min_wait=1,
        retry_max_wait=2,
    )

    # Verify that the LLM has the default temperature of 0.0
    assert llm.temperature == 0.0

    # Try to use the completion API with temperature=1.0 override - this should work
    messages = [{"role": "user", "content": "Hello, GPT-5-mini!"}]

    response = llm.completion(messages=messages, temperature=1.0)

    # Verify the response
    assert response is not None
    assert response.choices[0].message.content == "Test response from GPT-5-mini"  # type: ignore

    # Verify that the mock was called with temperature=1.0 (overridden)
    mock_completion.assert_called_once()
    call_kwargs = mock_completion.call_args[1]
    assert call_kwargs.get("temperature") == 1.0
