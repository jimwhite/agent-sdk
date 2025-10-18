"""
Example: Responses API path via LiteLLM in a Real Agent Conversation

- Runs a real Agent/Conversation to verify /responses path works
- Demonstrates rendering of Responses reasoning within normal conversation events
"""

from __future__ import annotations

import json
import os

from pydantic import SecretStr

from openhands.sdk import (
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.llm import LLM
from openhands.sdk.llm.utils.telemetry import Telemetry
from openhands.tools.preset.default import get_default_agent


logger = get_logger(__name__)

if not getattr(Telemetry, "_prompt_logging_patched", False):
    _original_on_request = Telemetry.on_request

    def _on_request_with_prompt_logging(self, log_ctx):
        result = _original_on_request(self, log_ctx)
        if isinstance(log_ctx, dict):
            prompt_payload = None
            if log_ctx.get("messages"):
                prompt_payload = log_ctx["messages"]
            else:
                prompt_payload = {
                    "instructions": log_ctx.get("instructions"),
                    "input": log_ctx.get("input"),
                }

            if prompt_payload:
                print("\n=== Prompt sent to LLM ===")
                print(json.dumps(prompt_payload, indent=2, ensure_ascii=False))
                print("=== End of prompt ===\n")
        return result

    Telemetry.on_request = _on_request_with_prompt_logging
    setattr(Telemetry, "_prompt_logging_patched", True)


api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
assert api_key, "Set LLM_API_KEY or OPENAI_API_KEY in your environment."

model = os.getenv("OPENAI_RESPONSES_MODEL", "openai/gpt-5-mini")
base_url = os.getenv("LITELLM_BASE_URL", "https://llm-proxy.eval.all-hands.dev")
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

llm = LLM(
    model=model,
    api_key=SecretStr(api_key),
    base_url=base_url,
    # Responses-path options
    reasoning_effort="high",
    # Logging / behavior tweaks
    log_completions=False,
    log_completions_folder=log_dir,
    drop_params=True,
    service_id="agent",
)
print("\n=== Agent Conversation using /responses path ===")
agent = get_default_agent(
    llm=llm,
    cli_mode=True,  # disable browser tools for env simplicity
)

llm_messages = []  # collect raw LLM-convertible messages for inspection


def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())


conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback],
    workspace=os.getcwd(),
)

# Keep the tasks short for demo purposes
conversation.send_message("Read the repo and write one fact into FACTS.txt.")
conversation.run()

conversation.send_message("Now delete FACTS.txt.")
conversation.run()

print("=" * 100)
print("Conversation finished. Got the following LLM messages:")
for i, message in enumerate(llm_messages):
    ms = str(message)
    print(f"Message {i}: {ms[:200]}{'...' if len(ms) > 200 else ''}")
