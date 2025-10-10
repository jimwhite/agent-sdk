# Kubernetes Build Context Generator

This directory contains a script to generate a tar.gz file with everything needed to build the OpenHands Agent Server in a Kubernetes environment.

## Script: `create_k8s_build_context.sh`

### Purpose

The `create_k8s_build_context.sh` script creates a self-contained tar.gz archive that includes:
- A standalone Dockerfile (copied from the original with all dependencies)
- Complete source code (openhands/ directory)
- All necessary configuration files (pyproject.toml, uv.lock, etc.)
- Build instructions and documentation

This is designed for Kubernetes environments where you need to upload a build context that will be built remotely.

### Usage

#### Basic Usage
```bash
./openhands/agent_server/docker/create_k8s_build_context.sh
```

This creates `./k8s-build/agent-server-{SHORT_SHA}-python.tar.gz` with the default binary target, where `{SHORT_SHA}` is the first 7 characters of the current git commit hash.

#### Advanced Usage

You can customize the build using environment variables:

```bash
# Create a minimal build context
TARGET=binary-minimal ./openhands/agent_server/docker/create_k8s_build_context.sh

# Use a different output directory and custom filename
OUTPUT_DIR=./my-builds OUTPUT_NAME=agent-server-v1.0.tar.gz ./openhands/agent_server/docker/create_k8s_build_context.sh

# Use a different base image
BASE_IMAGE=ubuntu:22.04 ./openhands/agent_server/docker/create_k8s_build_context.sh

# Don't clean the output directory (useful for multiple builds)
CLEAN_OUTPUT=false ./openhands/agent_server/docker/create_k8s_build_context.sh
```

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OUTPUT_DIR` | `./k8s-build` | Directory where the tar.gz will be created |
| `OUTPUT_NAME` | *(auto-generated)* | Custom name for output file. If not set, uses `agent-server-{SHORT_SHA}-{PRIMARY_TAG}.tar.gz` |
| `BASE_IMAGE` | `nikolaik/python-nodejs:python3.12-nodejs22` | Base Docker image to use |
| `CUSTOM_TAGS` | `python` | Comma-separated tags (first one used in filename) |
| `TARGET` | `binary` | Docker build target (binary, binary-minimal, source, source-minimal) |
| `CLEAN_OUTPUT` | `true` | Whether to clean the output directory before building |

### File Naming

By default, the script generates filenames using the same tagging format as the Docker build system:

```
agent-server-{SHORT_SHA}-{PRIMARY_TAG}.tar.gz
```

Where:
- `{SHORT_SHA}`: First 7 characters of the current git commit hash
- `{PRIMARY_TAG}`: First tag from `CUSTOM_TAGS` (default: "python")

Examples:
- `agent-server-189979a-python.tar.gz` (default)
- `agent-server-189979a-nodejs.tar.gz` (with `CUSTOM_TAGS=nodejs`)
- `agent-server-abc1234-python.tar.gz` (different commit)

You can override this by setting `OUTPUT_NAME` explicitly.

### Build Targets

The generated Dockerfile supports multiple build targets:

- **`binary`**: Production binary with full features (Docker, VNC, VSCode Web)
- **`binary-minimal`**: Production binary with minimal features (headless)
- **`source`**: Development mode with source code and virtual environment
- **`source-minimal`**: Development mode with minimal features

### Output Structure

The generated tar.gz contains:

```
├── Dockerfile                 # Standalone multi-stage Dockerfile
├── BUILD_INSTRUCTIONS.md      # Detailed build and usage instructions
├── pyproject.toml             # Root project configuration
├── uv.lock                    # Locked dependencies
├── README.md                  # Project README
├── LICENSE                    # Project license
└── openhands/                 # Complete source code
    ├── agent_server/          # Agent server implementation
    ├── sdk/                   # OpenHands SDK
    ├── tools/                 # OpenHands tools
    └── workspace/             # Workspace management
```

### Example Kubernetes Usage

1. **Generate the build context:**
   ```bash
   ./openhands/agent_server/docker/create_k8s_build_context.sh
   ```

2. **Upload to your Kubernetes build system:**
   ```bash
   # Example with a generic build system
   kubectl create configmap agent-server-build --from-file=k8s-build/openhands-agent-server-k8s-build.tar.gz
   ```

3. **Extract and build in Kubernetes:**
   ```bash
   # In your Kubernetes build pod
   tar -xzf openhands-agent-server-k8s-build.tar.gz
   docker build -t openhands-agent-server .
   ```

### Comparison with Original Build Script

| Feature | Original `build.sh` | New `create_k8s_build_context.sh` |
|---------|--------------------|------------------------------------|
| Purpose | Direct Docker build | Generate portable build context |
| Dependencies | Requires full repo checkout | Self-contained tar.gz |
| Caching | Uses Docker layer caching | Includes everything for remote build |
| Tagging | Automatic Git-based tagging | Manual tagging after build |
| CI Integration | GitHub Actions optimized | Generic Kubernetes compatible |

### Troubleshooting

#### Common Issues

1. **"No such file or directory" errors:**
   - Ensure you're running the script from the repository root
   - Check that all required files exist in the repository

2. **Large tar.gz file:**
   - The archive includes the complete source code and dependencies
   - Typical size is around 400-500KB
   - Use `binary-minimal` target for smaller builds

3. **Build failures in Kubernetes:**
   - Ensure your Kubernetes environment has sufficient resources
   - Check that the base image is accessible from your cluster
   - Verify Docker buildx is available if using multi-platform builds

#### Validation

To validate the generated build context:

```bash
# Extract and test locally
mkdir test-build && cd test-build
tar -xzf ../k8s-build/openhands-agent-server-k8s-build.tar.gz
docker build --target binary-minimal -t test-agent-server .
```

### Integration Examples

#### GitLab CI
```yaml
build-agent-server:
  script:
    - ./openhands/agent_server/docker/create_k8s_build_context.sh
    - tar -xzf k8s-build/openhands-agent-server-k8s-build.tar.gz
    - docker build -t $CI_REGISTRY_IMAGE/agent-server:$CI_COMMIT_SHA .
```

#### Jenkins
```groovy
stage('Build Agent Server') {
    steps {
        sh './openhands/agent_server/docker/create_k8s_build_context.sh'
        sh 'tar -xzf k8s-build/openhands-agent-server-k8s-build.tar.gz'
        sh 'docker build -t agent-server:${BUILD_NUMBER} .'
    }
}
```

#### Tekton Pipeline
```yaml
- name: build-agent-server
  image: docker:latest
  script: |
    ./openhands/agent_server/docker/create_k8s_build_context.sh
    tar -xzf k8s-build/openhands-agent-server-k8s-build.tar.gz
    docker build -t $(params.image-name) .
```