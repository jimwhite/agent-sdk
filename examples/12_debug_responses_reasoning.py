import json
import os

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    LLMConvertibleEvent,
    Message,
    TextContent,
    get_logger,
)
from openhands.tools import BashTool


logger = get_logger(__name__)
LOG_DIR = os.path.join(os.getcwd(), "logs", "reasoning")

api_key = os.getenv("LITELLM_API_KEY")
assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

# Choose a model that supports Responses API and reasoning
# You can switch to o1-preview or another reasoning-capable model through the proxy
MODEL = os.getenv("DEBUG_MODEL", "litellm_proxy/openai/gpt-5-mini-2025-08-07")

llm = LLM(
    model=MODEL,
    base_url="https://llm-proxy.eval.all-hands.dev",
    api_key=SecretStr(api_key),
    native_tool_calling=True,
    log_completions=True,
    log_completions_folder=LOG_DIR,
)

cwd = os.getcwd()
agent = Agent(llm=llm, tools=[BashTool.create(working_dir=cwd)])

llm_messages = []


def cb(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())


conv = Conversation(agent=agent, callbacks=[cb])
conv.send_message(
    message=Message(
        role="user",
        content=[
            TextContent(
                text=(
                    "Echo 'Hello' using a tool call. "
                    "Also explain briefly why you're doing it."
                )
            )
        ],
    )
)
conv.run()

# Dump out a small artifact from the last run.
# The Telemetry will also write a rich JSON file.
os.makedirs(LOG_DIR, exist_ok=True)
artifact_path = os.path.join(LOG_DIR, "12_debug_responses_reasoning.last.json")
meta = {
    "model": MODEL,
    "supports_responses": llm.is_responses_api_supported(),
    "fc_active": llm.is_function_calling_active(),
}
with open(artifact_path, "w") as f:
    json.dump(
        {"meta": meta, "messages": [m.model_dump() for m in llm_messages]}, f, indent=2
    )

print("=" * 100)
print(f"Saved debug artifact to: {artifact_path}")
print(f"Model: {MODEL}")
print(f"Responses supported: {meta['supports_responses']}")
print(f"Function calling active: {meta['fc_active']}")
print("Check logs/reasoning for Telemetry JSON with request/response context.")
