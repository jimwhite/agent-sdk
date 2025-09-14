import os

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    LLMConvertibleEvent,
    LLMRegistry,
    Message,
    TextContent,
    get_logger,
)
from openhands.sdk.event import ActionEvent
from openhands.tools import BashTool


logger = get_logger(__name__)
LOG_DIR = os.path.join(os.getcwd(), "logs", "reasoning")


# Configure LLM using LLMRegistry
api_key = os.getenv("LITELLM_API_KEY")
assert api_key is not None, "LITELLM_API_KEY environment variable is not set."

# Create LLM instance
main_llm = LLM(
    model="litellm_proxy/openai/gpt-5-mini-2025-08-07",
    base_url="https://llm-proxy.eval.all-hands.dev",
    api_key=SecretStr(api_key),
)

# Create LLM registry and add the LLM
llm_registry = LLMRegistry()
llm_registry.add("main_agent", main_llm)

# Get LLM from registry
llm = llm_registry.get("main_agent")

# Tools
cwd = os.getcwd()
tools = [BashTool.create(working_dir=cwd)]


def ensure_dir(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


# Agent
agent = Agent(llm=llm, tools=tools)

llm_messages = []  # collect raw LLM messages
last_path_kind = None  # "chat" or "responses"
last_reasoning = None  # any extracted reasoning content if present


def conversation_callback(event: Event):
    global last_path_kind, last_reasoning
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())
    # Capture the LLM path (chat vs responses) and reasoning when available
    if isinstance(event, ActionEvent) and event.kind == "llm_complete":
        payload = getattr(event, "payload", {}) or {}
        last_path_kind = payload.get("kind")
        # In responses path, our converter may include reasoning_content on the message
        try:
            choice0 = payload.get("response", {}).get("choices", [{}])[0]
            msg = choice0.get("message", {})
            last_reasoning = msg.get("reasoning_content")
        except Exception:
            last_reasoning = None


conversation = Conversation(agent=agent, callbacks=[conversation_callback])

conversation.send_message(
    message=Message(
        role="user",
        content=[TextContent(text="Please echo 'Hello!' using a tool call.")],
    )
)
conversation.run()

# Persist a debug artifact so we can inspect what happened
ensure_dir(LOG_DIR)
try:
    with open(os.path.join(LOG_DIR, "05_use_llm_registry.last.json"), "w") as f:
        import json

        json.dump(
            {
                "path_kind": last_path_kind,
                "reasoning": last_reasoning,
                "messages": llm_messages,
            },
            f,
            default=lambda o: getattr(o, "model_dump", lambda: str(o))(),
            indent=2,
        )
except Exception:
    pass

print("=" * 100)
print("Conversation finished. Got the following LLM messages:")
for i, message in enumerate(llm_messages):
    print(f"Message {i}: {str(message)[:200]}")

print("=" * 100)
print(f"LLM path kind: {last_path_kind}")
print(f"Reasoning (if any): {last_reasoning}")
print(f"LLM Registry services: {llm_registry.list_services()}")

# Demonstrate getting the same LLM instance from registry
same_llm = llm_registry.get("main_agent")
print(f"Same LLM instance: {llm is same_llm}")

# Demonstrate requesting a completion directly from an LLM
completion_response = llm.completion(
    messages=[{"role": "user", "content": "Say hello in one word."}]
)
# Access the response content
if completion_response.choices and completion_response.choices[0].message:  # type: ignore
    content = completion_response.choices[0].message.content  # type: ignore
    print(f"Direct completion response: {content}")
    print(f"Type of content: {type(content)}")
    print(f"Full response object: {completion_response.choices[0].message}")  # type: ignore
else:
    print("No response content available")
