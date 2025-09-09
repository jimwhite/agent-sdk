# LLM Providers

This directory contains detailed configuration guides for various LLM providers supported by the OpenHands Agent SDK.

## Quick Start

```python
from pydantic import SecretStr
from openhands.sdk import LLM

# Basic usage with any provider
llm = LLM(
    model="provider/model-name",
    api_key=SecretStr("your-api-key"),
)
```

## Provider Guides

### Cloud Providers
- **[OpenAI](openai-llms.md)** - GPT-4o, GPT-4, GPT-3.5 models
- **[Azure OpenAI](azure-llms.md)** - Azure-hosted OpenAI models
- **[Google](google-llms.md)** - Gemini models
- **[Groq](groq.md)** - Fast inference with Llama and other models
- **[OpenRouter](openrouter.md)** - Access to multiple providers through one API
- **[Moonshot](moonshot.md)** - Kimi models
- **[OpenHands Cloud](openhands-llms.md)** - OpenHands-hosted models

### Local & Self-Hosted
- **[Local LLMs](local-llms.md)** - Ollama, vLLM, SGLang setup
- **[LiteLLM Proxy](litellm-proxy.md)** - Self-hosted LiteLLM proxy server

### Advanced Configuration
- **[Custom LLM Configurations](custom-llm-configs.md)** - Advanced customization options

## Overview

For general information about LLM configuration, model recommendations, and best practices, see the [main LLM documentation](llms.md).

## Environment Variables

Common environment variables that work across providers:

```python
import os

# Retry configuration
os.environ["LLM_NUM_RETRIES"] = "5"
os.environ["LLM_RETRY_MIN_WAIT"] = "5"
os.environ["LLM_RETRY_MAX_WAIT"] = "30"

# Feature toggles
os.environ["LLM_DISABLE_VISION"] = "true"
os.environ["LLM_CACHING_PROMPT"] = "true"
```

## Loading from Configuration Files

```python
# From environment variables
llm = LLM.load_from_env()

# From TOML file
llm = LLM.load_from_toml("config.toml")

# From JSON file
llm = LLM.load_from_json("config.json")
```