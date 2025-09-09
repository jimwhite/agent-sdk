# Openrouter

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="anthropic/claude-sonnet-4-20250514",
    api_key=SecretStr("your-anthropic-api-key"),
)
```

# Openrouter

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

When using the agent-sdk, you'll need to set the following in the agent-sdk LLM configuration:
* `LLM Provider` to `OpenRouter`
* `LLM Model` to the model you will be using.
[Visit here to see a full list of OpenRouter models](https://openrouter.ai/models).
If the model is not in the list, enable `Advanced` options, and enter it in
`Custom Model` (e.g. openrouter/<model-name> like `openrouter/anthropic/claude-3.5-sonnet`).
* `API Key` to your OpenRouter API key.