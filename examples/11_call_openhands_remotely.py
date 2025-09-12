"""
Example 11: Call OpenHands remotely via REST API.

This example mirrors 01_hello_world.py but runs the conversation against a
server via HTTP. It will:
  1) start the OpenHands server (from source, using uv if available)
  2) verify /docs and OpenAPI JSON
  3) construct LLM/Agent/Conversation on the server through REST API
  4) run the hello-world flow remotely

Notes:
  - Requires server dependencies (fastapi, uvicorn) and SDK dependencies
    (litellm). Use `make build` first.
  - The server must be reachable at localhost:55848.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
from pydantic import SecretStr

from openhands.sdk.client import RuntimeGateway
from openhands.tools import BashTool, FileEditorTool, TaskTrackerTool


ROOT = Path(__file__).resolve().parents[1]


def build_executable() -> bool:
    script = ROOT / "openhands" / "server" / "build.py"
    print(f"[build] Running: uv run python {script}")
    r = subprocess.run(["uv", "run", "python", str(script), "--no-test"], text=True)
    ok = r.returncode == 0
    print(f"[build] success={ok}")
    return ok


def start_server() -> subprocess.Popen:
    env = {
        **os.environ,
        "OPENHANDS_MASTER_KEY": os.environ.get("OPENHANDS_MASTER_KEY", "local-dev"),
    }
    exe = (
        ROOT
        / "dist"
        / ("openhands-server.exe" if os.name == "nt" else "openhands-server")
    )
    if exe.exists():
        cmd = [str(exe), "--host", "0.0.0.0", "--port", "55848"]
    else:
        cmd = [
            "uv",
            "run",
            "openhandsd",
            "--host",
            "0.0.0.0",
            "--port",
            "55848",
        ]

    print("[server]", " ".join(cmd))
    return subprocess.Popen(cmd, env=env, cwd=str(ROOT))


def wait_alive(base_url: str, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    with httpx.Client(timeout=2.0) as client:
        while time.time() < deadline:
            try:
                r = client.get(base_url + "/alive")
                if r.status_code == 200:
                    print("[check] /alive:", r.json())
                    return
            except Exception:
                pass
            time.sleep(0.5)
    raise RuntimeError("Server did not become ready in time")


def check_docs(base_url: str) -> None:
    with httpx.Client(timeout=5.0) as client:
        r = client.get(base_url + "/openapi.json")
        r.raise_for_status()
        r = client.get(base_url + "/docs")
        r.raise_for_status()


def main() -> int:
    # 1) start server
    proc = start_server()
    base_url = "http://localhost:55848"
    try:
        # 2) health + docs
        wait_alive(base_url)
        check_docs(base_url)

        # 3) client: register models
        api_key = os.environ.get("OPENHANDS_MASTER_KEY", "local-dev")
        with RuntimeGateway(base_url, api_key=api_key) as gw:
            # register models used by RPC wire codec
            from openhands.sdk import LLM, Agent, Conversation, Message, TextContent

            gw.register_models(
                {
                    "Message": Message,
                    "TextContent": TextContent,
                    "Agent": Agent,
                    "Conversation": Conversation,  # not used as BaseModel, but safe
                    "LLM": LLM,
                }
            )
            gw.sync_routes()

            # 4) remotely construct LLM/Agent/Conversation and run flow
            api_key = os.getenv("LITELLM_API_KEY")
            assert api_key, "Set LITELLM_API_KEY for the LLM provider"

            llm = LLM(
                model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
                base_url="https://llm-proxy.eval.all-hands.dev",
                api_key=SecretStr(api_key),
            )
            tools = [
                BashTool.create(working_dir=os.getcwd()),
                FileEditorTool.create(),
                TaskTrackerTool.create(save_dir=os.getcwd()),
            ]
            agent = Agent(llm=llm, tools=tools)

            # 3a) Create the remote Conversation instance using the new REST API
            RemoteConversation = gw.bind(Conversation)
            conv = RemoteConversation(
                agent=agent,
                visualize=False,
            )
            print("Created remote conversation successfully")

            # send messages + run (remotely)
            conv.send_message(
                message=Message(
                    role="user",
                    content=[
                        TextContent(
                            text=(
                                "Hello! Can you create a new Python file named hello.py"
                                " that prints 'Hello, World!'? Use task tracker to "
                                "plan your steps."
                            )
                        )
                    ],
                )
            )
            conv.run()

            conv.send_message(
                message=Message(
                    role="user",
                    content=[TextContent(text=("Great! Now delete that file."))],
                )
            )
            conv.run()

        print("Done: remote conversation executed.")
        return 0
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
