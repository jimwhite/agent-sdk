"""
Example: Call Anthropic thinking model via LiteLLM and print typed thinking blocks.

Requirements
- Set LITELLM_API_KEY in your environment
- Ensure network access to the LiteLLM proxy (default below)

Run
  uv run python examples/12_anthropic_thinking_litellm.py
"""

import os
from typing import Any

from pydantic import SecretStr

from openhands.sdk import LLM, Message, TextContent, get_logger


logger = get_logger(__name__)


def main() -> None:
    api_key = os.getenv("LITELLM_API_KEY")
    assert api_key, "LITELLM_API_KEY environment variable is not set."

    # Anthropic thinking model via LiteLLM proxy
    # Note: reasoning_effort defaults to "high" in our LLM class (except Gemini 2.5)
    llm = LLM(
        model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
        timeout=120,
    )

    # Simple prompt encouraging a short chain-of-thought
    user = Message(
        role="user",
        content=[
            TextContent(
                text=(
                    "You are solving a quick math puzzle. "
                    "Explain your reasoning briefly, then give the final answer "
                    "at the end on a new line labeled 'Answer:'.\n\n"
                    "Question: If Alice has 12 apples and gives 5 to Bob, "
                    "how many apples does she have left?"
                )
            )
        ],
    )

    # Call the LLM
    resp = llm.completion(messages=[user])
    # Handle both non-streaming and streaming ModelResponse types
    choice0 = resp.choices[0]
    litellm_msg = getattr(choice0, "message", None) or getattr(choice0, "delta", None)
    assert litellm_msg is not None, "Unexpected LiteLLM response choice structure"

    # Print the raw assistant text
    print("== Assistant content ==")
    print(getattr(litellm_msg, "content", ""))

    # Print Anthropic-style provider-normalized reasoning fields if present
    rc = getattr(litellm_msg, "reasoning_content", None)
    if rc:
        print("\n== reasoning_content ==")
        print(rc)

    tbs: list[dict[str, Any]] | None = getattr(litellm_msg, "thinking_blocks", None)
    if tbs:
        print("\n== thinking_blocks (typed) ==")
        for i, blk in enumerate(tbs, 1):
            btype = (
                blk.get("type") if isinstance(blk, dict) else getattr(blk, "type", None)
            )
            if btype == "thinking":
                text = (
                    blk.get("thinking")
                    if isinstance(blk, dict)
                    else getattr(blk, "thinking", "")
                )
            elif btype == "redacted_thinking":
                text = "[redacted]"
            else:
                text = str(blk)
            print(f"Block {i} [{btype}]: {text}")

    # Show SDK mapping also preserves these fields
    sdk_msg = Message.from_litellm_message(litellm_msg)
    print("\n== SDK Message fields ==")
    print("reasoning_content:", sdk_msg.reasoning_content)
    print("thinking_blocks present:", bool(sdk_msg.thinking_blocks))
    print("provider_specific_fields present:", bool(sdk_msg.provider_specific_fields))


if __name__ == "__main__":
    main()
