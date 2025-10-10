# Runtime Build Context Generator

This directory contains a script to generate a complete build context for the OpenHands Agent Server that can be used in runtime environments, including Kubernetes and Runtime API deployments.

## Overview

The `build_for_runtime_api.sh` script creates a tar.gz file containing:
- A standalone Dockerfile (no external dependencies)
- Complete source code
- All necessary dependencies
- Build instructions

This allows you to upload the tar.gz to a runtime environment where the actual Docker build will be performed. If Runtime API credentials are provided, the script will automatically upload and monitor the build process.

## Prerequisites

- `tar` and `gzip` utilities
- `curl` (for Runtime API uploads)
- `base64` (for Runtime API uploads)
- `jq` (optional, for better JSON parsing)

## Usage

### Basic Usage

```bash
./openhands/agent_server/docker/build_for_runtime_api.sh
```

This creates `./runtime-build/agent-server-{SHORT_SHA}-{PRIMARY_TAG}.tar.gz` with everything needed to build the agent server.

### Runtime API Integration

To automatically upload to a Runtime API:

```bash
RUNTIME_API_URL="https://your-runtime-api.com" \
RUNTIME_API_KEY="your-api-key" \
./openhands/agent_server/docker/build_for_runtime_api.sh
```

The script will:
1. Create the build context tar.gz
2. Upload it to the `/build` endpoint
3. Poll the `/build_status` endpoint until completion
4. Report the final build status and image name

### Configuration Options

The script supports several environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `OUTPUT_DIR` | `./runtime-build` | Directory where the build context will be created |
| `BASE_IMAGE` | `nikolaik/python-nodejs:python3.12-nodejs22` | Base Docker image to use |
| `TARGET` | `binary` | Build target (binary, binary-minimal, source, source-minimal) |
| `CLEAN_OUTPUT` | `true` | Whether to clean the output directory before building |
| `CUSTOM_TAGS` | `python` | Comma-separated list of custom tags |
| `OUTPUT_NAME` | (auto-generated) | Custom filename for the output tar.gz |
| `RUNTIME_API_URL` | (empty) | Runtime API base URL for automatic upload |
| `RUNTIME_API_KEY` | (empty) | Runtime API authentication key |

### Examples

#### Local build only
```bash
./openhands/agent_server/docker/build_for_runtime_api.sh
```

#### Upload to Runtime API
```bash
RUNTIME_API_URL="https://runtime-api.example.com" \
RUNTIME_API_KEY="your-secret-key" \
./openhands/agent_server/docker/build_for_runtime_api.sh
```

#### Custom base image and target
```bash
BASE_IMAGE="python:3.12-slim" TARGET="binary-minimal" ./openhands/agent_server/docker/build_for_runtime_api.sh
```

#### Custom output directory and filename
```bash
OUTPUT_DIR="./my-builds" OUTPUT_NAME="my-agent-server.tar.gz" ./openhands/agent_server/docker/build_for_runtime_api.sh
```

#### Multiple tags
```bash
CUSTOM_TAGS="nodejs,python,dev" ./openhands/agent_server/docker/build_for_runtime_api.sh
```

## Filename Convention

By default, the script generates filenames using the same format as the Docker build system:

```
agent-server-{SHORT_SHA}-{PRIMARY_TAG}.tar.gz
```

Where:
- `SHORT_SHA`: First 7 characters of the git commit SHA
- `PRIMARY_TAG`: First tag from CUSTOM_TAGS (or "python" if not specified)

Examples:
- `agent-server-0506352-python.tar.gz` (default)
- `agent-server-0506352-nodejs.tar.gz` (with CUSTOM_TAGS=nodejs)
- `agent-server-0506352-dev.tar.gz` (with CUSTOM_TAGS=dev,staging)

## Runtime API Integration

### API Endpoints

The script interacts with two Runtime API endpoints:

1. **POST `/build`**: Upload build context and initiate build
   - Accepts JSON payload with `context` (base64-encoded tar.gz) and `target_image` fields
   - Returns JSON with `build_id` for tracking

2. **GET `/build_status?build_id={id}`**: Check build status
   - Returns JSON with `status` field and optional `image`/`error` fields
   - Status values: `PENDING`, `QUEUED`, `RUNNING`, `SUCCESS`, `FAILURE`, `INTERNAL_ERROR`, `TIMEOUT`, `CANCELLED`, `EXPIRED`

### Authentication

The script uses the `X-API-Key` header for authentication:

```bash
curl -H "X-API-Key: your-api-key" -F "context=@build.tar.gz" -F "target_image=my-image" https://api.example.com/build
```

### Build Monitoring

The script polls the build status every 30 seconds with a 30-minute timeout. Build progress is displayed in real-time:

```
[runtime-build] Build initiated with ID: abc123
[runtime-build] Build status: PENDING
[runtime-build] Build status: RUNNING
[runtime-build] Build status: SUCCESS
[runtime-build] ✅ Build completed successfully!
[runtime-build] 🎉 Image: registry.example.com/agent-server:abc123
```

## Output Structure

The generated tar.gz contains:

```
./
├── Dockerfile              # Standalone, multi-stage Dockerfile
├── BUILD_INSTRUCTIONS.md   # Detailed build instructions
├── pyproject.toml          # Python project configuration
├── uv.lock                 # Locked dependencies
├── LICENSE                 # License file
├── README.md               # Project documentation
└── openhands/              # Complete source code
    └── agent_server/       # Agent server implementation
        ├── app.py
        ├── dependencies.py
        └── ...
```

## Using in Kubernetes

1. **Extract the archive:**
   ```bash
   tar -xzf agent-server-{SHORT_SHA}-{PRIMARY_TAG}.tar.gz
   ```

2. **Build the Docker image:**
   ```bash
   docker build -t openhands-agent-server .
   ```

3. **Run the container:**
   ```bash
   docker run -p 8000:8000 openhands-agent-server
   ```

## Build Targets

The script supports different build targets:

- **`binary`** (default): Full build with all dependencies
- **`binary-minimal`**: Minimal build with only essential dependencies
- **`source`**: Source-based build (development mode)
- **`source-minimal`**: Minimal source build

## Advanced Usage

### Custom Dockerfile Modifications

The generated Dockerfile is a multi-stage build that you can customize:

```dockerfile
# Add custom build args
ARG CUSTOM_ARG=default_value

# Add custom dependencies in the base stage
RUN apt-get update && apt-get install -y custom-package

# Modify the final stage
FROM app AS binary
RUN echo "Custom configuration" > /app/config.txt
```

### Integration with CI/CD

```yaml
# Example GitHub Actions workflow
- name: Generate runtime build context
  run: |
    ./openhands/agent_server/docker/build_for_runtime_api.sh
    
- name: Upload to Runtime API
  env:
    RUNTIME_API_URL: ${{ secrets.RUNTIME_API_URL }}
    RUNTIME_API_KEY: ${{ secrets.RUNTIME_API_KEY }}
  run: |
    ./openhands/agent_server/docker/build_for_runtime_api.sh
```

### Error Handling

The script includes comprehensive error handling:

- **Upload failures**: HTTP error codes and response bodies are displayed
- **Build failures**: Error messages from the Runtime API are shown
- **Timeouts**: 30-minute timeout with clear messaging
- **Network issues**: Retry logic for transient failures

## Troubleshooting

### Common Issues

1. **Permission denied**: Make sure the script is executable
   ```bash
   chmod +x ./openhands/agent_server/docker/build_for_runtime_api.sh
   ```

2. **Git not found**: The script requires git to generate the SHA
   ```bash
   # Install git if not available
   apt-get update && apt-get install -y git
   ```

3. **Runtime API authentication**: Verify your API key and URL
   ```bash
   curl -H "X-API-Key: your-key" https://your-api.com/build_status?build_id=test
   ```

4. **Large archive size**: The archive includes all source code and dependencies
   - Use `binary-minimal` or `source-minimal` targets for smaller builds
   - Check that unnecessary files are excluded

### Validation

To validate the generated build context:

```bash
# Extract and test build
tar -xzf agent-server-*.tar.gz -C /tmp/test-build
cd /tmp/test-build
docker build -t test-agent-server .
docker run --rm test-agent-server python -c "import openhands.agent_server; print('OK')"
```

### Runtime API Debugging

Enable verbose output for API debugging:

```bash
# Test API connectivity
curl -v -H "X-API-Key: your-key" https://your-api.com/build_status?build_id=test

# Check build logs (if supported by your Runtime API)
curl -H "X-API-Key: your-key" https://your-api.com/build_logs?build_id=your-build-id
```

## Related Files

- `build.sh`: Main Docker build script (for local development)
- `Dockerfile`: Original Dockerfile (requires build context setup)
- `agent-server.spec`: PyInstaller specification for binary builds