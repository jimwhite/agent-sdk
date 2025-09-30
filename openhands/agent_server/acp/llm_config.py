"""LLM configuration management for ACP server."""

import logging
from typing import Any

from pydantic import SecretStr

from openhands.sdk import LLM


logger = logging.getLogger(__name__)


def validate_llm_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate and sanitize LLM configuration."""
    # Define allowed LLM configuration parameters based on the LLM class
    allowed_params = {
        "model",
        "api_key",
        "base_url",
        "api_version",
        "aws_access_key_id",
        "aws_secret_access_key",
        "aws_region_name",
        "openrouter_site_url",
        "openrouter_app_name",
        "num_retries",
        "retry_multiplier",
        "retry_min_wait",
        "retry_max_wait",
        "timeout",
        "max_message_chars",
        "temperature",
        "top_p",
        "top_k",
        "custom_llm_provider",
        "max_input_tokens",
        "max_output_tokens",
        "input_cost_per_token",
        "output_cost_per_token",
        "ollama_base_url",
        "drop_params",
        "modify_params",
        "disable_vision",
        "disable_stop_word",
        "caching_prompt",
        "log_completions",
        "log_completions_folder",
        "custom_tokenizer",
        "native_tool_calling",
        "reasoning_effort",
        "seed",
        "safety_settings",
    }

    # Filter and validate configuration
    validated_config = {}
    for key, value in config.items():
        if key in allowed_params and value is not None:
            validated_config[key] = value
        elif key not in allowed_params:
            logger.warning(f"Unknown LLM parameter ignored: {key}")

    return validated_config


def create_llm_from_config(llm_config: dict[str, Any]) -> LLM:
    """Create an LLM instance using stored configuration or defaults."""
    import os

    # Start with default configuration
    llm_kwargs: dict[str, Any] = {
        "service_id": "acp-agent",
        "model": "claude-sonnet-4-20250514",  # Default model
    }

    # Apply user-provided configuration from authentication
    if llm_config:
        # Type-safe update of configuration
        for key, value in llm_config.items():
            llm_kwargs[key] = value
        logger.info(f"Using authenticated LLM config: {list(llm_config.keys())}")
    else:
        # Fallback to environment variables if no auth config provided
        logger.info("No authenticated LLM config, using environment/defaults")

        # Try to get API key from environment
        api_key = os.getenv("LITELLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            llm_kwargs["api_key"] = api_key

            # Configure for litellm proxy if available
            if os.getenv("LITELLM_API_KEY"):
                llm_kwargs.update(
                    {
                        "model": "litellm_proxy/anthropic/claude-sonnet-4-5-20250929",
                        "base_url": "https://llm-proxy.eval.all-hands.dev",
                        "drop_params": True,
                    }
                )
            else:
                llm_kwargs["model"] = "gpt-4o-mini"
        else:
            logger.warning("No API key found. Agent responses may not work.")
            llm_kwargs["api_key"] = "dummy-key"

    # Convert api_key to SecretStr if it's a string
    if "api_key" in llm_kwargs and isinstance(llm_kwargs["api_key"], str):
        llm_kwargs["api_key"] = SecretStr(llm_kwargs["api_key"])

    # Convert other secret fields to SecretStr if needed
    secret_fields = ["aws_access_key_id", "aws_secret_access_key"]
    for field in secret_fields:
        if field in llm_kwargs and isinstance(llm_kwargs[field], str):
            llm_kwargs[field] = SecretStr(llm_kwargs[field])

    logger.info(f"Creating LLM with model: {llm_kwargs.get('model', 'unknown')}")
    return LLM(**llm_kwargs)
