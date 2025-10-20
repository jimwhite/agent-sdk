from typing import Any
from unittest.mock import Mock, patch

import pytest
from litellm.exceptions import (
    RateLimitError,
)
from pydantic import SecretStr

from openhands.sdk.llm import LLM, LLMResponse, Message, TextContent
from openhands.sdk.llm.exceptions import LLMNoResponseError
from openhands.sdk.llm.utils.metrics import Metrics, TokenUsage

# Import common test utilities
from tests.conftest import create_mock_litellm_response


@pytest.fixture
def default_llm():
    return LLM(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        usage_id="default-test-llm",
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )


def test_llm_init_with_default_config(default_llm):
    """Test LLM initialization with default config using fixture."""
    assert default_llm.model == "gpt-4o"
    assert (
        default_llm.api_key is not None
        and default_llm.api_key.get_secret_value() == "test_key"
    )
    assert isinstance(default_llm.metrics, Metrics)
    assert default_llm.metrics.model_name == "gpt-4o"


@patch("openhands.sdk.llm.llm.httpx.get")
def test_base_url_for_openhands_provider(mock_get):
    """Test that openhands/ prefix automatically sets base_url to production proxy."""
    # Mock the model info fetch to avoid actual HTTP calls to production
    mock_get.return_value = Mock(json=lambda: {"data": []})

    llm = LLM(
        model="openhands/claude-sonnet-4-20250514",
        api_key=SecretStr("test-key"),
        usage_id="test-openhands-llm",
    )
    assert llm.base_url == "https://llm-proxy.app.all-hands.dev/"
    mock_get.assert_called_once()


def test_llm_service_id_alias_uses_usage_id():
    legacy_kwargs: dict[str, Any] = {
        "model": "alias-model",
        "service_id": "legacy",
    }
    with pytest.warns(DeprecationWarning):
        llm = LLM(**legacy_kwargs)  # type: ignore[arg-type]
    assert llm.usage_id == "legacy"


def test_token_usage_add():
    """Test that TokenUsage instances can be added together."""
    # Create two TokenUsage instances
    usage1 = TokenUsage(
        model="model1",
        prompt_tokens=10,
        completion_tokens=5,
        cache_read_tokens=3,
        cache_write_tokens=2,
        response_id="response-1",
    )

    usage2 = TokenUsage(
        model="model2",
        prompt_tokens=8,
        completion_tokens=6,
        cache_read_tokens=2,
        cache_write_tokens=4,
        response_id="response-2",
    )

    # Add them together
    combined = usage1 + usage2

    # Verify the result
    assert combined.model == "model1"  # Should keep the model from the first instance
    assert combined.prompt_tokens == 18  # 10 + 8
    assert combined.completion_tokens == 11  # 5 + 6
    assert combined.cache_read_tokens == 5  # 3 + 2
    assert combined.cache_write_tokens == 6  # 2 + 4
    assert (
        combined.response_id == "response-1"
    )  # Should keep the response_id from the first instance


def test_metrics_merge_accumulated_token_usage():
    """Test that accumulated token usage is properly merged between two Metrics
    instances."""
    # Create two Metrics instances
    metrics1 = Metrics(model_name="model1")
    metrics2 = Metrics(model_name="model2")

    # Add token usage to each
    metrics1.add_token_usage(10, 5, 3, 2, 1000, "response-1")
    metrics2.add_token_usage(8, 6, 2, 4, 1000, "response-2")

    # Verify initial accumulated token usage
    metrics1_data = metrics1.get()
    accumulated1 = metrics1_data["accumulated_token_usage"]
    assert accumulated1["prompt_tokens"] == 10
    assert accumulated1["completion_tokens"] == 5
    assert accumulated1["cache_read_tokens"] == 3
    assert accumulated1["cache_write_tokens"] == 2

    metrics2_data = metrics2.get()
    accumulated2 = metrics2_data["accumulated_token_usage"]
    assert accumulated2["prompt_tokens"] == 8
    assert accumulated2["completion_tokens"] == 6
    assert accumulated2["cache_read_tokens"] == 2
    assert accumulated2["cache_write_tokens"] == 4

    # Merge metrics2 into metrics1
    metrics1.merge(metrics2)

    # Verify merged accumulated token usage
    merged_data = metrics1.get()

    merged_accumulated = merged_data["accumulated_token_usage"]
    assert merged_accumulated["prompt_tokens"] == 18  # 10 + 8
    assert merged_accumulated["completion_tokens"] == 11  # 5 + 6
    assert merged_accumulated["cache_read_tokens"] == 5  # 3 + 2
    assert merged_accumulated["cache_write_tokens"] == 6  # 2 + 4


def test_metrics_diff():
    """Test that metrics diff correctly calculates the difference between two
    metrics."""
    # Create baseline metrics
    baseline = Metrics(model_name="test-model")
    baseline.add_cost(1.0)
    baseline.add_token_usage(10, 5, 2, 1, 1000, "baseline-response")
    baseline.add_response_latency(0.5, "baseline-response")

    # Create current metrics with additional data
    current = Metrics(model_name="test-model")
    current.merge(baseline)  # Start with baseline
    current.add_cost(2.0)  # Add more cost
    current.add_token_usage(15, 8, 3, 2, 1000, "current-response")  # Add more tokens
    current.add_response_latency(0.8, "current-response")  # Add more latency

    # Calculate diff
    diff = current.diff(baseline)

    # Verify diff contains only the additional data
    diff_data = diff.get()
    assert diff_data["accumulated_cost"] == 2.0  # Only the additional cost
    assert len(diff_data["costs"]) == 1  # Only the additional cost entry
    assert len(diff_data["token_usages"]) == 1  # Only the additional token usage
    assert len(diff_data["response_latencies"]) == 1  # Only the additional latency

    # Verify accumulated token usage diff
    accumulated_diff = diff_data["accumulated_token_usage"]
    assert accumulated_diff["prompt_tokens"] == 15  # Only the additional tokens
    assert accumulated_diff["completion_tokens"] == 8
    assert accumulated_diff["cache_read_tokens"] == 3
    assert accumulated_diff["cache_write_tokens"] == 2


@patch("openhands.sdk.llm.llm.litellm_completion")
def test_llm_completion_with_mock(mock_completion):
    """Test LLM completion with mocked litellm."""
    mock_response = create_mock_litellm_response("Test response")
    mock_completion.return_value = mock_response

    # Create LLM after the patch is applied
    llm = LLM(
        usage_id="test-llm",
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )

    # Test completion
    messages = [Message(role="user", content=[TextContent(text="Hello")])]
    response = llm.completion(messages=messages)

    assert isinstance(response, LLMResponse)
    assert response.raw_response == mock_response
    mock_completion.assert_called_once()


@patch("openhands.sdk.llm.llm.litellm_completion")
def test_llm_retry_on_rate_limit(mock_completion):
    """Test that LLM retries on rate limit errors."""
    mock_response = create_mock_litellm_response("Success after retry")

    mock_completion.side_effect = [
        RateLimitError(
            message="Rate limit exceeded",
            llm_provider="test_provider",
            model="test_model",
        ),
        mock_response,
    ]

    # Create LLM after the patch is applied
    llm = LLM(
        usage_id="test-llm",
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )

    # Test completion with retry
    messages = [Message(role="user", content=[TextContent(text="Hello")])]
    response = llm.completion(messages=messages)

    assert isinstance(response, LLMResponse)
    assert response.raw_response == mock_response
    assert mock_completion.call_count == 2  # First call failed, second succeeded


def test_llm_cost_calculation(default_llm):
    """Test LLM cost calculation and metrics tracking."""
    llm = default_llm

    # Test cost addition
    initial_cost = llm.metrics.accumulated_cost
    llm.metrics.add_cost(1.5)
    assert llm.metrics.accumulated_cost == initial_cost + 1.5

    # Test cost validation
    with pytest.raises(ValueError, match="Added cost cannot be negative"):
        llm.metrics.add_cost(-1.0)


def test_llm_token_counting(default_llm):
    """Test LLM token counting functionality."""
    llm = default_llm

    # Test with dict messages
    messages = [
        Message(role="user", content=[TextContent(text="Hello")]),
        Message(role="assistant", content=[TextContent(text="Hi there!")]),
    ]

    # Token counting might return 0 if model not supported, but should not error
    token_count = llm.get_token_count(messages)
    assert isinstance(token_count, int)
    assert token_count >= 0


def test_llm_vision_support(default_llm):
    """Test LLM vision support detection."""
    llm = default_llm

    # Vision support detection should work without errors
    vision_active = llm.vision_is_active()
    assert isinstance(vision_active, bool)


def test_llm_function_calling_support(default_llm):
    """Test LLM function calling support detection."""
    llm = default_llm

    # Function calling support detection should work without errors
    function_calling_active = llm.is_function_calling_active()
    assert isinstance(function_calling_active, bool)


def test_llm_caching_support(default_llm):
    """Test LLM prompt caching support detection."""
    llm = default_llm

    # Caching support detection should work without errors
    caching_active = llm.is_caching_prompt_active()
    assert isinstance(caching_active, bool)


def test_llm_string_representation(default_llm):
    """Test LLM string representation."""
    llm = default_llm

    str_repr = str(llm)
    # Pydantic models don't show "LLM(" prefix in str(), just the field values
    assert "gpt-4o" in str_repr
    assert "model=" in str_repr

    repr_str = repr(llm)
    # repr() shows "LLM(" prefix, str() doesn't
    assert "LLM(" in repr_str
    assert "gpt-4o" in repr_str


def test_llm_local_detection_based_on_model_name(default_llm):
    """Test LLM local model detection based on model name."""
    llm = default_llm

    # Test basic model configuration
    assert llm.model == "gpt-4o"
    assert llm.temperature == 0.0

    # Test with localhost base_url
    local_llm = default_llm.model_copy(update={"base_url": "http://localhost:8000"})
    assert local_llm.base_url == "http://localhost:8000"

    # Test with ollama model
    ollama_llm = default_llm.model_copy(update={"model": "ollama/llama2"})
    assert ollama_llm.model == "ollama/llama2"


def test_llm_local_detection_based_on_base_url():
    """Test local model detection based on base_url."""
    # Test with localhost base_url
    local_llm = LLM(
        model="gpt-4o", base_url="http://localhost:8000", usage_id="test-llm"
    )
    assert local_llm.base_url == "http://localhost:8000"

    # Test with 127.0.0.1 base_url
    local_llm_ip = LLM(
        model="gpt-4o", base_url="http://127.0.0.1:8000", usage_id="test-llm"
    )
    assert local_llm_ip.base_url == "http://127.0.0.1:8000"

    # Test with remote model
    remote_llm = LLM(
        model="gpt-4o", base_url="https://api.openai.com/v1", usage_id="test-llm"
    )
    assert remote_llm.base_url == "https://api.openai.com/v1"


def test_llm_openhands_provider_rewrite(default_llm):
    """Test LLM message formatting for different message types."""
    llm = default_llm

    # Test with single Message object in a list
    message = [Message(role="user", content=[TextContent(text="Hello")])]
    formatted = llm.format_messages_for_llm(message)
    assert isinstance(formatted, list)
    assert len(formatted) == 1
    assert isinstance(formatted[0], dict)

    # Test with list of Message objects
    messages = [
        Message(role="user", content=[TextContent(text="Hello")]),
        Message(role="assistant", content=[TextContent(text="Hi there!")]),
    ]
    formatted = llm.format_messages_for_llm(messages)
    assert isinstance(formatted, list)
    assert len(formatted) == 2
    assert all(isinstance(msg, dict) for msg in formatted)


def test_metrics_copy():
    """Test that metrics can be copied correctly."""
    original = Metrics(model_name="test-model")
    original.add_cost(1.0)
    original.add_token_usage(10, 5, 2, 1, 1000, "test-response")
    original.add_response_latency(0.5, "test-response")

    # Create a copy
    copied = original.deep_copy()

    # Verify copy has same data
    original_data = original.get()
    copied_data = copied.get()

    assert original_data["accumulated_cost"] == copied_data["accumulated_cost"]
    assert len(original_data["costs"]) == len(copied_data["costs"])
    assert len(original_data["token_usages"]) == len(copied_data["token_usages"])
    assert len(original_data["response_latencies"]) == len(
        copied_data["response_latencies"]
    )

    # Verify they are independent (modifying one doesn't affect the other)
    copied.add_cost(2.0)
    assert original.accumulated_cost != copied.accumulated_cost


def test_metrics_log():
    """Test metrics logging functionality."""
    metrics = Metrics(model_name="test-model")
    metrics.add_cost(1.5)
    metrics.add_token_usage(10, 5, 2, 1, 1000, "test-response")

    log_output = metrics.log()
    assert isinstance(log_output, str)
    assert "accumulated_cost" in log_output
    assert "1.5" in log_output


def test_llm_config_validation():
    """Test LLM configuration validation."""
    # Test with minimal valid config
    llm = LLM(model="gpt-4o", usage_id="test-llm")
    assert llm.model == "gpt-4o"

    # Test with full config
    full_llm = LLM(
        usage_id="test-llm",
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        base_url="https://api.openai.com/v1",
        temperature=0.7,
        max_output_tokens=1000,
        num_retries=3,
        retry_min_wait=1,
        retry_max_wait=10,
    )
    assert full_llm.temperature == 0.7
    assert full_llm.max_output_tokens == 1000


@patch("openhands.sdk.llm.llm.litellm_completion")
def test_llm_no_response_error(mock_completion):
    """Test handling of LLMNoResponseError."""
    from litellm.types.utils import ModelResponse, Usage

    # Mock empty response using proper ModelResponse
    mock_response = ModelResponse(
        id="test-id",
        choices=[],  # Empty choices should trigger LLMNoResponseError
        created=1234567890,
        model="gpt-4o",
        object="chat.completion",
        usage=Usage(prompt_tokens=10, completion_tokens=0, total_tokens=10),
    )
    mock_completion.return_value = mock_response

    # Create LLM after the patch is applied
    llm = LLM(
        usage_id="test-llm",
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        num_retries=2,
        retry_min_wait=1,
        retry_max_wait=2,
    )

    # Test that empty response raises LLMNoResponseError
    messages = [Message(role="user", content=[TextContent(text="Hello")])]
    with pytest.raises(LLMNoResponseError):
        llm.completion(messages=messages)


def test_response_latency_tracking(default_llm):
    """Test response latency tracking in metrics."""
    metrics = Metrics(model_name="test-model")

    # Add some latencies
    metrics.add_response_latency(0.5, "response-1")
    metrics.add_response_latency(1.2, "response-2")
    metrics.add_response_latency(0.8, "response-3")

    latencies = metrics.response_latencies
    assert len(latencies) == 3
    assert latencies[0].latency == 0.5
    assert latencies[1].latency == 1.2
    assert latencies[2].latency == 0.8

    # Test negative latency is converted to 0
    metrics.add_response_latency(-0.1, "response-4")
    assert metrics.response_latencies[-1].latency == 0.0


def test_token_usage_context_window():
    """Test token usage with context window tracking."""
    usage = TokenUsage(
        model="test-model",
        prompt_tokens=100,
        completion_tokens=50,
        context_window=4096,
        response_id="test-response",
    )

    assert usage.context_window == 4096
    assert usage.per_turn_token == 0  # Default value

    # Test addition preserves max context window
    usage2 = TokenUsage(
        model="test-model",
        prompt_tokens=200,
        completion_tokens=75,
        context_window=8192,
        response_id="test-response-2",
    )

    combined = usage + usage2
    assert combined.context_window == 8192  # Should take the max
    assert combined.prompt_tokens == 300
    assert combined.completion_tokens == 125


# Telemetry Tests


def test_telemetry_cost_calculation_header_exception():
    """Test telemetry cost calculation handles header parsing exceptions."""
    from unittest.mock import Mock, patch

    from openhands.sdk.llm.utils.metrics import Metrics
    from openhands.sdk.llm.utils.telemetry import Telemetry

    # Create a mock response with headers that will cause an exception
    mock_response = Mock()
    mock_response.headers = {"x-litellm-cost": "invalid-float"}

    metrics = Metrics()
    telemetry = Telemetry(model_name="test-model", metrics=metrics)

    # Mock the logger to capture debug messages
    with patch("openhands.sdk.llm.utils.telemetry.logger") as mock_logger:
        # Mock litellm_completion_cost to return a valid cost
        with patch(
            "openhands.sdk.llm.utils.telemetry.litellm_completion_cost",
            return_value=0.001,
        ):
            cost = telemetry._compute_cost(mock_response)

            # Should fall back to litellm cost calculator
            assert cost == 0.001

            # Should have logged the debug message for header parsing failure (line 139)
            mock_logger.debug.assert_called_once()
            assert "Failed to get cost from LiteLLM headers:" in str(
                mock_logger.debug.call_args
            )


def test_gpt5_enable_encrypted_reasoning_default():
    """
    Test that enable_encrypted_reasoning is enabled for GPT-5 models in Responses API.
    """
    # Test with gpt-5 model - should auto-enable in _normalize_responses_kwargs
    llm = LLM(
        model="openai/gpt-5-mini",
        api_key=SecretStr("test_key"),
        usage_id="test-gpt5-llm",
    )
    # Field default is False, but _normalize_responses_kwargs will enable it
    assert llm.enable_encrypted_reasoning is False

    # Test that the normalization actually enables it
    from openhands.sdk.llm.options.responses_options import select_responses_options

    normalized = select_responses_options(llm, {}, include=None, store=None)
    assert "include" in normalized
    assert "reasoning.encrypted_content" in normalized["include"]

    # Test with litellm_proxy/openai/gpt-5 model
    llm_proxy = LLM(
        model="litellm_proxy/openai/gpt-5-codex",
        api_key=SecretStr("test_key"),
        usage_id="test-gpt5-proxy-llm",
    )
    normalized_proxy = select_responses_options(llm_proxy, {}, include=None, store=None)
    assert "include" in normalized_proxy
    assert "reasoning.encrypted_content" in normalized_proxy["include"]

    # Test that explicit True is respected
    llm_explicit = LLM(
        model="openai/gpt-5-mini",
        api_key=SecretStr("test_key"),
        enable_encrypted_reasoning=True,
        usage_id="test-gpt5-explicit-llm",
    )
    assert llm_explicit.enable_encrypted_reasoning is True
    normalized_explicit = select_responses_options(
        llm_explicit, {}, include=None, store=None
    )
    assert "reasoning.encrypted_content" in normalized_explicit["include"]

    # Encrypted reasoning is included when stateless (store=False)
    llm_gpt4 = LLM(
        model="gpt-4o",
        api_key=SecretStr("test_key"),
        usage_id="test-gpt4-llm",
    )
    assert llm_gpt4.enable_encrypted_reasoning is False
    normalized_gpt4 = select_responses_options(llm_gpt4, {}, include=None, store=None)
    assert "reasoning.encrypted_content" in normalized_gpt4.get("include", [])
    # But if store=True, it should not be included
    normalized_gpt4_store = select_responses_options(
        llm_gpt4, {}, include=None, store=True
    )
    assert "reasoning.encrypted_content" not in normalized_gpt4_store.get("include", [])


# LLM Registry Tests
