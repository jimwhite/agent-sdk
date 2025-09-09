# OpenAI

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="openai/gpt-4o",
    api_key=SecretStr("your-openai-api-key"),
)
```

# OpenAI

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="openai/gpt-4o",
    api_key=SecretStr("your-openai-api-key"),
)
```

## Configuration

When using the agent-sdk, you'll need to set the following in the agent-sdk LLM configuration:
* `LLM Provider` to `OpenAI`
* `LLM Model` to the model you will be using.
[Visit here to see a full list of OpenAI models that LiteLLM supports.](https://docs.litellm.ai/docs/providers/openai#openai-chat-completion-models)
If the model is not in the list, enable `Advanced` options, and enter it in `Custom Model` (e.g. openai/<model-name> like `openai/gpt-4o`).
* `API Key` to your OpenAI API key. To find or create your OpenAI Project API Key, [see here](https://platform.openai.com/api-keys).

## Using OpenAI-Compatible Endpoints

Just as for OpenAI Chat completions, we use LiteLLM for OpenAI-compatible endpoints. You can find their full documentation on this topic [here](https://docs.litellm.ai/docs/providers/openai_compatible).

## Using an OpenAI Proxy

If you're using an OpenAI proxy, in the agent-sdk LLM configuration:
1. Enable `Advanced` options
2. Set the following:
   - `Custom Model` to openai/<model-name> (e.g. `openai/gpt-4o` or openai/<proxy-prefix>/<model-name>)
   - `Base URL` to the URL of your OpenAI proxy
   - `API Key` to your OpenAI API key