"""
Example: Responses API path via LiteLLM + Real Agent Conversation

- Verifies direct LLM.responses() with reasoning include (prints reasoning summary if present)
- Runs a real Agent/Conversation (system prompt, tools, workspace) to ensure /responses path works end-to-end
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import SecretStr

from openhands.sdk import (
    Conversation,
    Event,
    LLMConvertibleEvent,
    get_logger,
)
from openhands.sdk.llm import LLM, Message, TextContent
from openhands.tools.preset.default import get_default_agent


logger = get_logger(__name__)


def print_assistant_and_reasoning(resp) -> None:
    # Assistant output
    print("\n=== Assistant Message (Direct responses()) ===")
    if resp.message.content:
        for part in resp.message.content:
            if isinstance(part, TextContent):
                print(part.text)
    else:
        print("(no assistant text content)")

    # Reasoning (from raw ResponsesAPIResponse)
    rr = getattr(resp.raw_response, "reasoning", None)
    if rr is not None:
        try:
            # Avoid logging encrypted content; handle dict or Pydantic model
            payload: dict[str, Any] = (
                rr.model_dump()
                if hasattr(rr, "model_dump")
                else (rr if isinstance(rr, dict) else {})
            )
            payload.pop("encrypted_content", None)
            print("\n=== Reasoning (sanitized) ===")
            # Print a compact view if possible
            effort = payload.get("effort")
            summary = payload.get("summary")
            status = payload.get("status")
            if effort is not None:
                print(f"effort: {effort}")
            if status is not None:
                print(f"status: {status}")
            if summary:
                print("summary:")
                # summary might be a list or string
                if isinstance(summary, list):
                    for s in summary:
                        print(f"- {s}")
                else:
                    print(f"- {summary}")
            # If there are additional keys, print as a fallback
            extra = {
                k: v
                for k, v in payload.items()
                if k not in {"effort", "summary", "status"}
            }
            if extra:
                print("extra:", extra)
        except Exception as e:
            print(f"(reasoning present but could not be printed due to error: {e})")
    else:
        print("\n(no reasoning object present)")


def run_direct_responses(llm: LLM) -> None:
    # Minimal turn for direct Responses call
    messages = [
        Message(
            role="system",
            content=[TextContent(text="You are a concise, helpful assistant.")],
        ),
        Message(
            role="user",
            content=[
                TextContent(
                    text="Summarize this repository's README in 3 bullet points. If you cannot access it, request the content succinctly."
                )
            ],
        ),
    ]

    # Call Responses API directly. enable_encrypted_reasoning on LLM ensures include is set.
    resp = llm.responses(
        messages=messages,
        tools=None,
        store=False,
    )
    print_assistant_and_reasoning(resp)

    print("\n=== Metrics Snapshot ===")
    print(resp.metrics.model_dump())


def run_agent_conversation(llm: LLM) -> None:
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
    conversation.send_message(
        "Read the current repo and write a single fact about the project into FACTS.txt."
    )
    conversation.run()

    conversation.send_message("Now delete FACTS.txt.")
    conversation.run()

    print("=" * 100)
    print("Conversation finished. Got the following LLM messages:")
    for i, message in enumerate(llm_messages):
        ms = str(message)
        print(f"Message {i}: {ms[:200]}{'...' if len(ms) > 200 else ''}")


def main():
    # Prefer proxy credentials commonly used in this repo's examples
    api_key = os.getenv("LITELLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    assert api_key, "Set LITELLM_API_KEY or OPENAI_API_KEY in your environment."

    model = os.getenv("OPENAI_RESPONSES_MODEL", "openai/gpt-5-mini")
    base_url = os.getenv("LITELLM_BASE_URL", "https://llm-proxy.eval.all-hands.dev")

    llm = LLM(
        model=model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        # Responses-path options
        enable_encrypted_reasoning=True,  # request encrypted reasoning passthrough
        reasoning_effort="high",
        # Logging / behavior tweaks
        log_completions=False,
        drop_params=True,
        service_id="agent",
    )

    # 1) Direct Responses API check with reasoning
    run_direct_responses(llm)

    # 2) Real Agent + Conversation round-trips relying on /responses routing for gpt-5 family
    run_agent_conversation(llm)


if __name__ == "__main__":
    main()
