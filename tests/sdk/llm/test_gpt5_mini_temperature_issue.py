"""Test for GPT-5-mini temperature issue with litellm_proxy.

This test reproduces the issue where GPT-5-mini requires temperature to be set to 1,
but the LLM class defaults to temperature=0.0, causing an error.

These tests use real LLM API calls and require LLM_API_KEY and LLM_BASE_URL
environment variables to be set.
"""

import os

import pytest
from pydantic import SecretStr

from openhands.sdk.llm import LLM


def get_llm_config():
    """Get LLM configuration from environment variables."""
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")

    if not api_key or not base_url:
        pytest.skip(
            "LLM_API_KEY and LLM_BASE_URL environment variables must be set "
            "to run real LLM tests"
        )

    return api_key, base_url


def test_gpt5_mini_temperature_issue_without_temperature():
    """Test that GPT-5-mini fails when temperature is not explicitly set to 1.

    This test reproduces the issue where GPT-5-mini requires temperature=1
    but the LLM class defaults to temperature=0.0, causing an error.
    """
    api_key, base_url = get_llm_config()

    # Create LLM with litellm_proxy/openai/gpt-5-mini without specifying temperature
    # This should use the default temperature=0.0
    llm = LLM(
        model="litellm_proxy/openai/gpt-5-mini",
        api_key=SecretStr(api_key),
        base_url=base_url,
        num_retries=1,  # Reduce retries for faster test
        retry_min_wait=1,
        retry_max_wait=2,
    )

    # Verify that the LLM has the default temperature of 0.0
    assert llm.temperature == 0.0

    # Try to use the completion API - this should fail with GPT-5-mini
    messages = [{"role": "user", "content": "Hello, GPT-5-mini!"}]

    # The exact error message may vary depending on the LLM proxy implementation
    # but it should fail when temperature is not 1.0 for GPT-5-mini
    with pytest.raises(Exception) as exc_info:
        llm.completion(messages=messages)

    # Check that the error is related to temperature requirements
    error_message = str(exc_info.value).lower()
    assert "temperature" in error_message or "parameter" in error_message


def test_gpt5_mini_works_with_temperature_1():
    """Test that GPT-5-mini works when temperature is explicitly set to 1.

    This test shows that the issue can be resolved by explicitly setting temperature=1.
    """
    api_key, base_url = get_llm_config()

    # Create LLM with litellm_proxy/openai/gpt-5-mini with temperature=1.0
    llm = LLM(
        model="litellm_proxy/openai/gpt-5-mini",
        api_key=SecretStr(api_key),
        base_url=base_url,
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
    assert len(response.choices) > 0
    assert response.choices[0].message.content is not None  # type: ignore
    assert len(response.choices[0].message.content.strip()) > 0  # type: ignore


def test_gpt5_mini_temperature_override_in_completion_call():
    """Test that temperature can be overridden in the completion call.

    This test shows that even if the LLM has a default temperature,
    it can be overridden in the completion call.
    """
    api_key, base_url = get_llm_config()

    # Create LLM with litellm_proxy/openai/gpt-5-mini with default temperature=0.0
    llm = LLM(
        model="litellm_proxy/openai/gpt-5-mini",
        api_key=SecretStr(api_key),
        base_url=base_url,
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
    assert len(response.choices) > 0
    assert response.choices[0].message.content is not None  # type: ignore
    assert len(response.choices[0].message.content.strip()) > 0  # type: ignore
