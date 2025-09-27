import argparse
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Reuse the built-in agent server app and VS Code endpoints
from openhands.agent_server.api import api as agent_api


app = FastAPI(title="VS Code Diff Demo")

# Mount the agent server under / (shares routes and lifespan to start VSCode service)
app.mount("/", agent_api)


@app.get("/static/index.html")
def demo_page():
    # Simple demo page that calls /api/vscode/url and opens it in a new tab
    html = (
        "<!doctype html>"
        "<html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<title>VS Code Diff Demo</title>"
        "</head>"
        "<body>"
        "<h1>VS Code Diff Demo</h1>"
        "<p>Click the button to open the embedded web VS Code (OpenVSCode Server)."
        " It will load the current workspace folder and you can use SCM to view diffs."
        "</p>"
        "<button id='open'>Open VS Code</button>"
        "<pre id='out'></pre>"
        "<script>"
        "document.getElementById('open').onclick = async () => {"
        "  const resp = await fetch('/api/vscode/url');"
        "  const data = await resp.json();"
        "  document.getElementById('out').textContent = JSON.stringify(data, null, 2);"
        "  if (data.url) { window.open(data.url, '_blank'); }"
        "};"
        "</script>"
        "</body>"
        "</html>"
    )
    return HTMLResponse(content=html)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Ensure the example uses a config that sets static files and enables VS Code
    os.environ["OPENHANDS_AGENT_SERVER_CONFIG_PATH"] = str(
        Path(__file__).with_name("config.json")
    )

    # Run the demo FastAPI app
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
