# LLM Configuration

The OpenHands SDK can connect to any LLM supported by [LiteLLM](https://docs.litellm.ai/docs/providers). However, it requires a powerful model to work effectively.

## Model Recommendations

Based on our evaluations of language models for coding tasks (using the SWE-bench dataset), we can provide some recommendations for model selection. Our latest benchmarking results can be found in [this spreadsheet](https://docs.google.com/spreadsheets/d/1wOUdFCMyY6Nt0AIqF705KN4JKOWgeI4wUGUP60krXXs/edit?gid=0).

Based on these findings and community feedback, these are the latest models that have been verified to work reasonably well with OpenHands:

### Cloud / API-Based Models

- [anthropic/claude-sonnet-4-20250514](https://www.anthropic.com/api) (recommended)
- [openai/gpt-5-2025-08-07](https://openai.com/api/) (recommended)
- [gemini/gemini-2.5-pro](https://blog.google/technology/google-deepmind/gemini-model-thinking-updates-march-2025/)
- [deepseek/deepseek-chat](https://api-docs.deepseek.com/)
- [moonshot/kimi-k2-0711-preview](https://platform.moonshot.ai/docs/pricing/chat#generation-model-kimi-k2)

If you have successfully run OpenHands with specific providers, we encourage you to open a PR to share your setup process to help others using the same provider!

For a full list of the providers and models available, please consult the [litellm documentation](https://docs.litellm.ai/docs/providers).

> **Warning**: OpenHands will issue many prompts to the LLM you configure. Most of these LLMs cost money, so be sure to set spending limits and monitor usage.

### Local / Self-Hosted Models

- [mistralai/devstral-small](https://www.all-hands.dev/blog/devstral-a-new-state-of-the-art-open-model-for-coding-agents) (20 May 2025) -- also available through [OpenRouter](https://openrouter.ai/mistralai/devstral-small:free)
- [all-hands/openhands-lm-32b-v0.1](https://www.all-hands.dev/blog/introducing-openhands-lm-32b----a-strong-open-coding-agent-model) (31 March 2025) -- also available through [OpenRouter](https://openrouter.ai/all-hands/openhands-lm-32b-v0.1)

### Known Issues

> **Warning**: As of July 2025, there are known issues with Gemini 2.5 Pro conversations taking longer than normal with OpenHands. We are continuing to investigate.

> **Note**: Most current local and open source models are not as powerful. When using such models, you may see long wait times between messages, poor responses, or errors about malformed JSON. OpenHands can only be as powerful as the models driving it. However, if you do find ones that work, please add them to the verified list above.

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

## LLM Configuration

The following parameters can be configured when creating an LLM instance:

- `model` - The model identifier (required)
- `api_key` - API key for authentication
- `base_url` - Custom API endpoint
- `temperature` - Controls randomness (default: 0.0)
- `max_output_tokens` - Maximum output tokens
- `num_retries` - Number of retry attempts (default: 5)
- `native_tool_calling` - Enable native function calling
- `disable_vision` - Disable image processing
- `log_completions` - Enable completion logging

Additional configuration options can be set through environment variables:

- `LLM_API_VERSION`
- `LLM_EMBEDDING_MODEL`
- `LLM_EMBEDDING_DEPLOYMENT_NAME`
- `LLM_DROP_PARAMS`
- `LLM_DISABLE_VISION`
- `LLM_CACHING_PROMPT`

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

## Model Customization

LLM providers have specific settings that can be customized to optimize their performance with OpenHands, such as:

- **Custom Tokenizers**: For specialized models, you can add a suitable tokenizer.
- **Native Tool Calling**: Toggle native function/tool calling capabilities.

## API Retries and Rate Limits

LLM providers typically have rate limits, sometimes very low, and may require retries. OpenHands will automatically retry requests if it receives a Rate Limit Error (429 error code).

You can customize these options as you need for the provider you're using. Check their documentation, and set the following environment variables to control the number of retries and the time between retries:

- `LLM_NUM_RETRIES` (Default of 4 times)
- `LLM_RETRY_MIN_WAIT` (Default of 5 seconds)
- `LLM_RETRY_MAX_WAIT` (Default of 30 seconds)
- `LLM_RETRY_MULTIPLIER` (Default of 2)

If you are running OpenHands in development mode, you can also set these options in the `config.toml` file:

```toml
[llm]
num_retries = 4
retry_min_wait = 5
retry_max_wait = 30
retry_multiplier = 2
```