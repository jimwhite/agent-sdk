# LiteLLM Proxy

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-anthropic-api-key"),
)
```

# LiteLLM Proxy

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-anthropic-api-key"),
)
```

## Configuration

To use LiteLLM proxy with OpenHands, you need to:

1. Set up a LiteLLM proxy server (see [LiteLLM documentation](https://docs.litellm.ai/docs/proxy/quick_start))
2. When using the agent-sdk, you'll need to set the following in the agent-sdk LLM configuration:
  * Enable `Advanced` options
  * `Custom Model` to the prefix `litellm_proxy/` + the model you will be using (e.g. `litellm_proxy/anthropic.claude-3-5-sonnet-20241022-v2:0`)
  * `Base URL` to your LiteLLM proxy URL (e.g. `https://your-litellm-proxy.com`)
  * `API Key` to your LiteLLM proxy API key

## Supported Models

The supported models depend on your LiteLLM proxy configuration. OpenHands supports any model that your LiteLLM proxy
is configured to handle.

Refer to your LiteLLM proxy configuration for the list of available models and their names.