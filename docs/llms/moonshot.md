# Moonshot

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="moonshot/kimi-k2-0711-preview",
    api_key=SecretStr("your-moonshot-api-key"),
)
```

# Moonshot

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="moonshot/kimi-k2-0711-preview",
    api_key=SecretStr("your-moonshot-api-key"),
)
```

## Using Moonshot AI with OpenHands

[Moonshot AI](https://platform.moonshot.ai/) offers several powerful models, including Kimi-K2, which has been verified to work well with OpenHands.

### Setup

1. Sign up for an account at [Moonshot AI Platform](https://platform.moonshot.ai/)
2. Generate an API key from your account settings
3. Configure OpenHands to use Moonshot AI:

| Setting | Value |
| --- | --- |
| LLM Provider | `moonshot` |
| LLM Model | `kimi-k2-0711-preview` |
| API Key | Your Moonshot API key |

### Recommended Models

- `moonshot/kimi-k2-0711-preview` - Kimi-K2 is Moonshot's most powerful model with a 131K context window, function calling support, and web search capabilities.