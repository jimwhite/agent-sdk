# Google

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="gemini/gemini-2.5-pro",
    api_key=SecretStr("your-google-api-key"),
)
```

# Google

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="gemini/gemini-2.5-pro",
    api_key=SecretStr("your-google-api-key"),
)
```

## Gemini - Google AI Studio Configs

When using the agent-sdk, you'll need to set the following in the agent-sdk LLM configuration:
- `LLM Provider` to `Gemini`
- `LLM Model` to the model you will be using.
If the model is not in the list, enable `Advanced` options, and enter it in `Custom Model`
(e.g. gemini/<model-name> like `gemini/gemini-2.0-flash`).
- `API Key` to your Gemini API key

## VertexAI - Google Cloud Platform Configs

To use Vertex AI through Google Cloud Platform when running OpenHands, you'll need to set the following environment
variables using `-e` in the agent-sdk configuration:

```
GOOGLE_APPLICATION_CREDENTIALS="<json-dump-of-gcp-service-account-json>"
VERTEXAI_PROJECT="<your-gcp-project-id>"
VERTEXAI_LOCATION="<your-gcp-location>"
```

Then set the following in the agent-sdk LLM configuration:
- `LLM Provider` to `VertexAI`
- `LLM Model` to the model you will be using.
If the model is not in the list, enable `Advanced` options, and enter it in `Custom Model`
(e.g. vertex_ai/<model-name>).