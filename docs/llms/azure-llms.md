# Azure OpenAI

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="azure/your-deployment-name",
    api_key=SecretStr("your-azure-api-key"),
    base_url="https://your-resource.openai.azure.com/",
)
```

# Azure OpenAI

## Basic Usage

```python
from pydantic import SecretStr
from openhands.sdk import LLM

llm = LLM(
    model="azure/your-deployment-name",
    api_key=SecretStr("your-azure-api-key"),
    base_url="https://your-resource.openai.azure.com/",
)
```

## Configuration

When using the agent-sdk with Azure OpenAI, you need to set the API version:

```python
import os
os.environ["LLM_API_VERSION"] = "2023-05-15"  # or your preferred API version
```

> **Note**: You will need your ChatGPT deployment name which can be found on the deployments page in Azure.

### Complete Configuration Example

```python
from pydantic import SecretStr
from openhands.sdk import LLM
import os

# Set the API version
os.environ["LLM_API_VERSION"] = "2023-05-15"

llm = LLM(
    model="azure/your-deployment-name",  # Replace with your deployment name
    api_key=SecretStr("your-azure-api-key"),
    base_url="https://your-resource.openai.azure.com/",  # Replace with your endpoint
)
```

### Additional Configuration

For more advanced Azure configurations, you may need to set additional environment variables:

```
LLM_API_VERSION="<api-version>"                                    # e.g. "2024-02-15-preview"
```