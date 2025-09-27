# VS Code Diff Demo (Agent Server)

This demo starts the Agent Server, serves a tiny static page, and provides a button to open the embedded VS Code web UI focused on your workspace. The plan is to use VS Code as the Diff experience in V1.

How to run:

```
uv run python examples/25_vscode_diff_demo/run.py --host 0.0.0.0 --port 8000
```

- Static page served at: http://localhost:8000/
- Get VS Code URL (JSON): GET http://localhost:8000/api/vscode/url

Note: If auth is enabled in your config, include the proper session header.
