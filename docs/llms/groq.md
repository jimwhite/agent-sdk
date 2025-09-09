# Groq

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="groq/llama-3.1-70b-versatile",
    api_key=SecretStr("your-groq-api-key"),
)
```

# Groq

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="groq/llama-3.1-70b-versatile",
    api_key=SecretStr("your-groq-api-key"),
)
```

## Configuration

When using the agent-sdk, you'll need to set the following in the agent-sdk LLM configuration:
- `LLM Provider` to `Groq`
- `LLM Model` to the model you will be using. [Visit here to see the list of
models that Groq hosts](https://console.groq.com/docs/models). If the model is not in the list,
enable `Advanced` options, and enter it in `Custom Model` (e.g. groq/<model-name> like `groq/llama3-70b-8192`).
- `API key` to your Groq API key. To find or create your Groq API Key, [see here](https://console.groq.com/keys).

## Using Groq as an OpenAI-Compatible Endpoint

The Groq endpoint for chat completion is [mostly OpenAI-compatible](https://console.groq.com/docs/openai). Therefore, you can access Groq models as you
would access any OpenAI-compatible endpoint. In the agent-sdk LLM configuration:
1. Enable `Advanced` options
2. Set the following:
   - `Custom Model` to the prefix `openai/` + the model you will be using (e.g. `openai/llama3-70b-8192`)
   - `Base URL` to `https://api.groq.com/openai/v1`
   - `API Key` to your Groq API key