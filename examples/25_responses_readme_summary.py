import os
import sys
from pathlib import Path

from pydantic import SecretStr

from openhands.sdk import LLM, Conversation, EventBase, LLMConvertibleEvent, get_logger
from openhands.sdk.preset.default import get_default_agent


# Ensure logs are written to logs/responses
os.environ.setdefault("LOG_TO_FILE", "1")
os.environ.setdefault("LOG_DIR", str(Path.cwd() / "logs" / "responses"))


logger = get_logger(__name__)


def main() -> int:
    api_key = os.getenv("LITELLM_API_KEY")
    if not api_key:
        print("ERROR: LITELLM_API_KEY is not set in environment.", file=sys.stderr)
        return 2

    logs_dir = Path(os.environ.get("LOG_DIR", Path.cwd() / "logs" / "responses"))
    logs_dir.mkdir(parents=True, exist_ok=True)

    llm = LLM(
        model="openai/gpt-5-mini",
        base_url="https://llm-proxy.eval.all-hands.dev",
        api_key=SecretStr(api_key),
        service_id="agent",
        log_completions=True,
        log_completions_folder=str(logs_dir),
    )

    cwd = os.getcwd()
    agent = get_default_agent(llm=llm, working_dir=cwd, cli_mode=True)

    llm_messages = []

    def on_event(e: EventBase):
        if isinstance(e, LLMConvertibleEvent):
            llm_messages.append(e.to_llm_message())

    convo = Conversation(agent=agent, callbacks=[on_event])

    target = Path(cwd) / "README_SUMMARY.md"

    user_prompt = (
        "Use tools to read the repository README (README.mdx or README.md), then "
        "write a concise summary to README_SUMMARY.md at repo root. Keep it under "
        "200 lines and focus on usage and architecture. Do not reply here; use tools."
    )

    convo.send_message(user_prompt)
    convo.run()

    ok = target.exists() and target.stat().st_size > 0

    print("=" * 80)
    print(f"Summary file exists: {ok}")
    if ok:
        print(f"Summary path: {target}")
        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            content = target.read_text(errors="ignore")
        print("--- README_SUMMARY.md (first 2000 chars) ---")
        print(content[:2000])
    else:
        print("README_SUMMARY.md was not created. Inspect the logs below.")

    print("--- Logs directory contents ---")
    for p in sorted(logs_dir.glob("**/*")):
        if p.is_file():
            print(f"LOG: {p} ({p.stat().st_size} bytes)")

    print("--- Collected LLM messages (truncated) ---")
    for i, m in enumerate(llm_messages):
        s = str(m)
        print(f"[{i}] {s[:500]}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
