# VSCode Settings Extension Work

## Branch
`vscode-settings-extension`

## What We've Done

### 1. Created VSCode Extension
- **Location**: `openhands/agent_server/vscode_extensions/openhands-settings/`
- **Structure**:
  - `src/extension.ts` - Main extension code that configures settings
  - `package.json` - Extension metadata (activates on startup with `"*"`)
  - `tsconfig.json` - TypeScript configuration

### 2. Extension Settings Applied
The extension automatically configures:
- `workbench.colorTheme`: "Default Dark+"
- `editor.fontSize`: 14
- `editor.tabSize`: 4
- `files.autoSave`: "afterDelay"
- `files.autoSaveDelay`: 1000
- `update.mode`: "none"
- `telemetry.telemetryLevel`: "off"
- `extensions.autoCheckUpdates`: false
- `extensions.autoUpdate`: false

### 3. Updated `vscode_service.py`
- **Path**: `openhands/agent_server/vscode_service.py`
- Extensions directory: `self.extensions_dir = self.openvscode_server_root / "extensions"`
  - Points to `/openhands/.openvscode-server/extensions`
- Added `_build_extensions()` method:
  - Iterates through all extensions in the directory
  - Runs `npm install && npm run compile` for each
- Modified `_start_vscode_process()`:
  - Conditionally passes `--extensions-dir` flag if directory exists

### 4. Updated Dockerfile
- **Path**: `openhands/agent_server/docker/Dockerfile`
- Added COPY commands in both `source` and `binary` targets:
  ```dockerfile
  COPY --chown=${USERNAME}:${USERNAME} --from=builder /agent-server/openhands/agent_server/vscode_extensions /openhands/.openvscode-server/extensions
  ```
- Extensions are copied from source code into VSCode server's extensions directory

### 5. Created Test Example
- **Path**: `examples/02_remote_agent_server/04_vscode_with_docker_sandboxed_server.py`
- Uses `DockerWorkspace` with `extra_ports=True`
- Exposes VSCode on port 8011
- Instructions for checking the extension settings

## Architecture Pattern
Following V0 approach:
- Extensions live in VSCode server's own directory: `/openhands/.openvscode-server/extensions/`
- Extensions are built at runtime when service starts
- No `.vsix` packaging needed - direct source copy

## Next Steps
1. Test the extension by running the example script
2. Verify settings are applied in VSCode Web
3. Check extension build logs in agent server output

## Testing Command
```bash
export LLM_API_KEY=your_key_here
uv run python examples/02_remote_agent_server/04_vscode_with_docker_sandboxed_server.py
```

Then access VSCode at: http://localhost:8011
