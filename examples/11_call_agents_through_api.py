import os
import time
import zipfile
import tempfile
from pathlib import Path
import urllib.request
import urllib.error

from pydantic import SecretStr

from openhands.sdk import LLM, OpenHandsClient, TextContent, ToolSpec

# Optional: start the server inside Docker using the runtime toolkit
USE_DOCKER = os.getenv("OH_USE_DOCKER_RUNTIME", "0").lower() in {"1", "true", "yes"}
SERVER_URL = os.getenv("OPENHANDS_SERVER_URL", "http://localhost:9000")
MASTER_KEY = os.getenv("MASTER_KEY", "test")

container_runtime = None

if USE_DOCKER:
    # Build and run the OpenHands server in Docker as a tiny, two-stage image
    from openhands.server.runtime import BuildSpec, DockerRuntime

    def make_repo_zip(root: Path, out_path: Path) -> Path:
        # Package the openhands/ directory (sdk, tools, server) into a zip
        # Excludes .git and virtualenvs for a small context
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p in root.rglob("*"):
                if "/.git" in str(p) or "/.venv" in str(p):
                    continue
                if p.is_file():
                    arcname = str(p.relative_to(root.parent))
                    zf.write(p, arcname)
        return out_path

    repo_root = Path(__file__).resolve().parents[1]
    openhands_dir = repo_root / "openhands"
    if not openhands_dir.is_dir():
        raise RuntimeError(f"Expected openhands/ at {openhands_dir}")

    tmp_zip = Path(tempfile.gettempdir()) / "openhands_bundle.zip"
    make_repo_zip(openhands_dir, tmp_zip)

    dockerfile_tpl = """
    {% set artifact='payload/openhands_bundle.zip' %}
    # Stage 1: build a standalone binary via PyInstaller
    FROM {{ base_image }} AS builder
    ARG DEBIAN_FRONTEND=noninteractive
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc unzip && rm -rf /var/lib/apt/lists/*
    WORKDIR /build
    COPY . /ctx
    RUN mkdir -p /src && unzip -q /ctx/{{ artifact }} -d /src
    # Install local packages first so "openhands-server" deps resolve from local
    RUN python -m pip install --no-cache-dir -U pip wheel setuptools \
        && python -m pip install --no-cache-dir pyinstaller>=6.15.0 \
        && python -m pip install --no-cache-dir -e /src/openhands/sdk -e /src/openhands/tools \
        && python -m pip install --no-cache-dir -e /src/openhands/server
    WORKDIR /src/openhands/server
    # Build the binary. Spec already includes hidden imports/data files.
    RUN pyinstaller -y openhands-server.spec && ls -la dist

    # Stage 2: runtime image with only the binary
    FROM {{ base_image }} AS runtime
    WORKDIR /app
    COPY --from=builder /src/openhands/server/dist/openhands-server /usr/local/bin/openhands-server
    EXPOSE 9000
    ENV MASTER_KEY=test
    CMD ["/usr/local/bin/openhands-server"]
    """

    spec = BuildSpec(
        base_image="python:3.12-slim",
        tag=os.getenv("OPENHANDS_SERVER_IMAGE", "openhands/server:pyinst-dev"),
        dockerfile_template_str=dockerfile_tpl,
        artifact_zip=str(tmp_zip),
        artifact_relpath="payload/openhands_bundle.zip",
        build_args={"DEBIAN_FRONTEND": "noninteractive"},
    )

    rt = DockerRuntime(name=os.getenv("OPENHANDS_SERVER_NAME", "openhands-server"))
    print("[docker] building image…")
    rt.build(spec)
    print(f"[docker] built {rt.image}")
    print("[docker] starting container…")
    rt.start(ports={9000: 9000})
    container_runtime = rt

    # Wait for health endpoint
    for _ in range(60):
        try:
            with urllib.request.urlopen(f"{SERVER_URL}/health", timeout=2) as resp:
                if resp.status == 200:
                    break
        except Exception:
            pass
        time.sleep(1)
    else:
        raise RuntimeError("Server did not become healthy in time")

LLM_API_KEY = os.getenv("LITELLM_API_KEY")
if not LLM_API_KEY:
    raise RuntimeError("LITELLM_API_KEY environment variable is not set.")

try:
    with OpenHandsClient(server_url=SERVER_URL, master_key=MASTER_KEY) as oh:
        print("Starting conversation…")

        working_dir = "/app" if USE_DOCKER else os.getcwd()
        conv_id, _state = oh.start_conversation(
            llm=LLM(
                model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
                api_key=SecretStr(LLM_API_KEY),
                base_url="https://llm-proxy.eval.all-hands.dev",
            ),
            tools=[
                ToolSpec(name="BashTool", params={"working_dir": working_dir}),
                ToolSpec(name="FileEditorTool", params={}),
            ],
            mcp_config=(
                {}
                if USE_DOCKER
                else {
                    "mcpServers": {
                        "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]}
                    }
                }
            ),
        )
        print("Conversation ID:", conv_id)

        # 1) Ask the agent to read the repo and write 3 facts into FACTS.txt
        oh.send_message(
            conversation_id=conv_id,
            content=[
                TextContent(
                    text="Read https://github.com/All-Hands-AI/OpenHands and "
                    "write 3 facts about the project into FACTS.txt."
                )
            ],
        )
        oh.wait_until_idle(conv_id)

        # 2) Ask the agent to delete the file
        oh.send_message(
            conversation_id=conv_id,
            content=[TextContent(text="Great! Now delete that file.")],
        )
        oh.wait_until_idle(conv_id)

        # Print compact view of LLM messages
        print("=" * 80)
        evts = oh.get_events(conv_id, start=0, limit=1000)
        print("Events:")
        for e in evts:
            print(e)
finally:
    if container_runtime is not None:
        print("[docker] stopping container…")
        container_runtime.stop(remove=True)
