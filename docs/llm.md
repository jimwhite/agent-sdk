# LLM Configuration System

The OpenHands SDK provides a powerful and flexible LLM configuration system built on top of [LiteLLM](https://docs.litellm.ai/docs/providers). This system allows you to connect to any LLM provider supported by LiteLLM while providing additional features like retry logic, prompt caching, function calling, and comprehensive telemetry.

## Overview

The LLM system consists of two main components:

- **LLM**: The core class that handles model configuration, API calls, and response processing
- **LLMRegistry**: A registry system for managing and reusing LLM instances across services

## Basic Usage

### Simple LLM Configuration

```python
from pydantic import SecretStr
from openhands.sdk import LLM

# Basic configuration
llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-api-key"),
)

# Make a completion request
response = llm.completion(
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

### Using LLM with Agent

```python
from openhands.sdk import Agent, Conversation, LLM, Message, TextContent
from openhands.tools import BashTool, FileEditorTool

llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-api-key"),
)

tools = [BashTool(working_dir=os.getcwd()), FileEditorTool()]
agent = Agent(llm=llm, tools=tools)
conversation = Conversation(agent=agent)

conversation.send_message(
    Message(role="user", content=[TextContent(text="Create a hello.py file")])
)
conversation.run()
```

## Supported Providers

The OpenHands SDK supports all LLM providers available through LiteLLM. Here are some commonly used providers:

### Cloud/API-Based Models

#### OpenAI
```python
llm = LLM(
    model="openai/gpt-4o",
    api_key=SecretStr("your-openai-api-key"),
)
```

#### Anthropic
```python
llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-anthropic-api-key"),
)
```

#### Google Gemini
```python
llm = LLM(
    model="gemini/gemini-2.5-pro",
    api_key=SecretStr("your-google-api-key"),
)
```

#### Azure OpenAI
```python
llm = LLM(
    model="azure/gpt-4o",
    api_key=SecretStr("your-azure-api-key"),
    base_url="https://your-resource.openai.azure.com/",
    api_version="2024-12-01-preview",  # Set automatically for Azure models
)
```

#### OpenRouter
```python
llm = LLM(
    model="openrouter/anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-openrouter-api-key"),
    openrouter_site_url="https://docs.all-hands.dev/",
    openrouter_app_name="OpenHands",
)
```

#### DeepSeek
```python
llm = LLM(
    model="deepseek/deepseek-chat",
    api_key=SecretStr("your-deepseek-api-key"),
)
```

### Local/Self-Hosted Models

#### Ollama
```python
llm = LLM(
    model="ollama/llama3.2",
    base_url="http://localhost:11434",
    ollama_base_url="http://localhost:11434",
)
```

#### LiteLLM Proxy
```python
llm = LLM(
    model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
    base_url="https://your-litellm-proxy.com",
    api_key=SecretStr("your-proxy-api-key"),
)
```

#### OpenHands Models
```python
# Using the openhands/ prefix automatically routes to the OpenHands LiteLLM proxy
llm = LLM(
    model="openhands/anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-api-key"),
)
```

## Configuration Options

### Core Parameters

- **model** (str): The model identifier (required)
- **api_key** (SecretStr | None): API key for authentication
- **base_url** (str | None): Custom base URL for the API endpoint
- **api_version** (str | None): API version (automatically set for Azure models)

### Sampling Parameters

- **temperature** (float | None): Controls randomness (default: 0.0)
- **top_p** (float | None): Nucleus sampling parameter (default: 1.0)
- **top_k** (float | None): Top-k sampling parameter
- **seed** (int | None): Random seed for reproducible outputs

### Token Limits

- **max_input_tokens** (int | None): Maximum input tokens (auto-detected from model info)
- **max_output_tokens** (int | None): Maximum output tokens
- **max_message_chars** (int): Approximate max characters per message (default: 30,000)

### Retry Configuration

- **num_retries** (int): Number of retry attempts (default: 5)
- **retry_multiplier** (float): Backoff multiplier (default: 8)
- **retry_min_wait** (int): Minimum wait time in seconds (default: 8)
- **retry_max_wait** (int): Maximum wait time in seconds (default: 64)

### Advanced Features

- **native_tool_calling** (bool | None): Enable native function calling if supported
- **disable_vision** (bool | None): Disable image processing for vision-capable models
- **caching_prompt** (bool): Enable prompt caching (default: True)
- **reasoning_effort** (Literal["low", "medium", "high", "none"] | None): Reasoning effort for compatible models
- **safety_settings** (list[dict] | None): Safety settings for Mistral AI and Gemini models

### Logging and Telemetry

- **log_completions** (bool): Enable completion logging (default: False)
- **log_completions_folder** (str): Directory for completion logs
- **custom_tokenizer** (str | None): Custom tokenizer for token counting

### Provider-Specific Options

- **aws_access_key_id** (SecretStr | None): AWS access key for Bedrock
- **aws_secret_access_key** (SecretStr | None): AWS secret key for Bedrock
- **aws_region_name** (str | None): AWS region for Bedrock
- **custom_llm_provider** (str | None): Custom provider identifier
- **drop_params** (bool): Allow LiteLLM to drop unsupported parameters (default: True)
- **modify_params** (bool): Allow LiteLLM to modify parameters (default: True)

## LLM Registry

The LLMRegistry allows you to manage multiple LLM instances and reuse them across different services:

```python
from openhands.sdk import LLM, LLMRegistry

# Create registry
registry = LLMRegistry()

# Add LLM instances
main_llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-api-key"),
)
registry.add("main_agent", main_llm)

# Retrieve LLM instances
llm = registry.get("main_agent")

# List all registered services
services = registry.list_services()
```

### Registry Events

You can subscribe to registry events to monitor LLM creation and updates:

```python
def on_llm_event(event):
    print(f"LLM event: {event.service_id} - {event.llm.model}")

registry.subscribe(on_llm_event)
```

## Loading Configuration

### From Environment Variables

```python
# Set environment variables with LLM_ prefix
# LLM_MODEL=anthropic/claude-sonnet-4-20250514
# LLM_API_KEY=your-api-key
# LLM_TEMPERATURE=0.1

llm = LLM.load_from_env()
```

### From TOML File

```python
# config.toml
[llm]
model = "anthropic/claude-sonnet-4-20250514"
api_key = "your-api-key"
temperature = 0.1
max_output_tokens = 4096

llm = LLM.load_from_toml("config.toml")
```

### From JSON File

```python
# config.json
{
  "model": "anthropic/claude-sonnet-4-20250514",
  "api_key": "your-api-key",
  "temperature": 0.1,
  "max_output_tokens": 4096
}

llm = LLM.load_from_json("config.json")
```

## Model Features and Capabilities

The LLM system automatically detects model capabilities:

```python
# Check if function calling is supported
if llm.is_function_calling_active():
    print("Model supports function calling")

# Check if vision is supported
if llm.vision_is_active():
    print("Model supports vision")

# Check if prompt caching is supported
if llm.is_caching_prompt_active():
    print("Model supports prompt caching")

# Get model information
model_info = llm.model_info
if model_info:
    print(f"Max tokens: {model_info.get('max_tokens')}")
```

## Error Handling and Retries

The LLM system automatically handles common API errors with exponential backoff:

- **APIConnectionError**: Network connectivity issues
- **RateLimitError**: API rate limit exceeded
- **ServiceUnavailableError**: Service temporarily unavailable
- **Timeout**: Request timeout
- **InternalServerError**: Server-side errors

You can customize retry behavior:

```python
llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-api-key"),
    num_retries=3,
    retry_min_wait=5,
    retry_max_wait=30,
    retry_multiplier=2,
)
```

## Token Counting

Get accurate token counts for your messages:

```python
from openhands.sdk import Message, TextContent

messages = [
    Message(role="user", content=[TextContent(text="Hello, world!")])
]

token_count = llm.get_token_count(messages)
print(f"Token count: {token_count}")
```

## Best Practices

### 1. Use Environment Variables for API Keys

```python
import os
from pydantic import SecretStr

api_key = os.getenv("ANTHROPIC_API_KEY")
llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr(api_key) if api_key else None,
)
```

### 2. Configure Appropriate Retry Settings

```python
# For production environments
llm = LLM(
    model="your-model",
    num_retries=5,
    retry_min_wait=8,
    retry_max_wait=64,
)
```

### 3. Use LLM Registry for Multiple Services

```python
registry = LLMRegistry()

# Different LLMs for different purposes
registry.add("fast_llm", LLM(model="openai/gpt-4o-mini"))
registry.add("powerful_llm", LLM(model="anthropic/claude-sonnet-4-20250514"))
```

### 4. Enable Logging for Debugging

```python
llm = LLM(
    model="your-model",
    log_completions=True,
    log_completions_folder="./llm_logs",
)
```

### 5. Optimize for Cost

```python
# Disable vision for cost savings
llm = LLM(
    model="openai/gpt-4o",
    disable_vision=True,
    max_output_tokens=1000,  # Limit output tokens
)
```

## Troubleshooting

### Common Issues

1. **Empty API Key**: The system automatically converts empty API keys to `None` to allow alternative authentication methods (e.g., AWS IAM roles).

2. **Model Not Found**: Ensure the model identifier follows the correct format for your provider.

3. **Rate Limiting**: Increase retry settings or implement request throttling.

4. **Token Limits**: Monitor token usage and adjust `max_output_tokens` as needed.

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

llm = LLM(model="your-model", log_completions=True)
```

## Migration from Other Systems

If you're migrating from other LLM libraries, here are some common patterns:

### From OpenAI Client

```python
# Before (OpenAI client)
from openai import OpenAI
client = OpenAI(api_key="your-key")
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello"}]
)

# After (OpenHands SDK)
from openhands.sdk import LLM
llm = LLM(model="openai/gpt-4o", api_key=SecretStr("your-key"))
response = llm.completion(
    messages=[{"role": "user", "content": "Hello"}]
)
```

### From LangChain

```python
# Before (LangChain)
from langchain.llms import OpenAI
llm = OpenAI(model_name="gpt-4o", openai_api_key="your-key")

# After (OpenHands SDK)
from openhands.sdk import LLM
llm = LLM(model="openai/gpt-4o", api_key=SecretStr("your-key"))
```

For more information about specific providers and advanced configurations, refer to the [LiteLLM documentation](https://docs.litellm.ai/docs/providers).