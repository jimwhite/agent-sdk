# LLM Configuration

Configure any LLM provider supported by [LiteLLM](https://docs.litellm.ai/docs/providers).

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-api-key"),
)

response = llm.completion(
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

## Providers

| Provider | Model Format | Example |
|----------|-------------|---------|
| OpenAI | `openai/gpt-4o` | `LLM(model="openai/gpt-4o", api_key=SecretStr("sk-..."))` |
| Anthropic | `anthropic/claude-sonnet-4-20250514` | `LLM(model="anthropic/claude-sonnet-4-20250514", api_key=SecretStr("sk-..."))` |
| Google | `gemini/gemini-2.5-pro` | `LLM(model="gemini/gemini-2.5-pro", api_key=SecretStr("..."))` |
| Azure | `azure/gpt-4o` | `LLM(model="azure/gpt-4o", api_key=SecretStr("..."), base_url="https://your-resource.openai.azure.com/")` |
| Ollama | `ollama/llama3.2` | `LLM(model="ollama/llama3.2", base_url="http://localhost:11434")` |
| OpenHands | `openhands/anthropic/claude-sonnet-4-20250514` | `LLM(model="openhands/anthropic/claude-sonnet-4-20250514", api_key=SecretStr("..."))` |

See [LiteLLM providers](https://docs.litellm.ai/docs/providers) for the complete list.

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | str | required | Model identifier |
| `api_key` | SecretStr | None | API key |
| `base_url` | str | None | Custom API endpoint |
| `temperature` | float | 0.0 | Randomness (0-1) |
| `max_output_tokens` | int | None | Output token limit |
| `num_retries` | int | 5 | Retry attempts |
| `native_tool_calling` | bool | None | Use native function calling |
| `disable_vision` | bool | None | Disable image processing |
| `log_completions` | bool | False | Log API calls |

```python
llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-key"),
    temperature=0.1,
    max_output_tokens=4096,
    num_retries=3,
)
```

## LLM Registry

Manage multiple LLM instances:

```python
from openhands.sdk import LLMRegistry

registry = LLMRegistry()
registry.add("main", llm)
llm = registry.get("main")
```

## Loading Configuration

```python
# From environment (LLM_MODEL, LLM_API_KEY, etc.)
llm = LLM.load_from_env()

# From TOML file
llm = LLM.load_from_toml("config.toml")

# From JSON file  
llm = LLM.load_from_json("config.json")
```

## Capabilities

```python
# Check model features
llm.is_function_calling_active()  # Function calling support
llm.vision_is_active()           # Vision support  
llm.is_caching_prompt_active()   # Prompt caching support

# Get token count
token_count = llm.get_token_count(messages)
```

## Error Handling

Automatic retry with exponential backoff for:
- Rate limits
- Network errors  
- Service unavailable
- Timeouts

Customize retry behavior:
```python
llm = LLM(
    model="your-model",
    num_retries=3,
    retry_min_wait=5,
    retry_max_wait=30,
)
```